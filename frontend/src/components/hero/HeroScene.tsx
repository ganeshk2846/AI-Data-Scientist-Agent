"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { HeroPoint, plotX, plotY, PLOT } from "@/lib/heroSeries";

/**
 * The hero's point field — the data itself, in three dimensions.
 *
 * Every point belongs to one row of the opening query's result. The field
 * arrives scattered through the depth of the scene and resolves over 2.4s into
 * the series: a dense band tracing the measure's own curve, with a thinner
 * drift of points filling the volume beneath it, so the shape has body rather
 * than being a line of dots. Nothing in the scene is a number of its own and
 * nothing here computes one — `plotX`/`plotY` place a point exactly as a
 * chart places a mark.
 *
 * The camera is **orthographic**, spanning -1..1 in both axes. That is what
 * lets the label layer above the canvas sit in the same coordinate space and
 * land its labels exactly on the points they name, at any size, with no
 * per-frame projection.
 *
 * Frame budget:
 *  - the fly-in, the idle drift and the pointer highlight are all in the
 *    vertex shader, so a frame costs three uniform writes and one draw call.
 *    The CPU does no per-point work after setup and allocates nothing;
 *  - `devicePixelRatio` is capped at 1.75;
 *  - the loop stops entirely when the canvas leaves the viewport or the tab is
 *    hidden, and resumes where it left off;
 *  - the caller does not mount this at all for reduced motion, a coarse
 *    pointer, a low-core device, a narrow viewport or a browser without WebGL.
 *    Those get the same composition drawn in the label layer alone.
 */

interface HeroSceneProps {
  points: HeroPoint[];
  /** Resolved design tokens, so the scene is lit by the same palette. */
  colors: { accent: string; muted: string };
  /** How the points sit on the ground: added to it, or laid on it. */
  blend: "add" | "normal";
  /** The point the pointer is nearest, highlighted in the field. */
  activeIndex: number | null;
  className?: string;
}

/** Points per row of the result, so density is the same whatever the row count. */
const PER_POINT = 320;
const MAX_POINTS = 5200;

const VERTEX = /* glsl */ `
  attribute vec3 aFrom;
  attribute vec3 aTo;
  attribute float aSeed;
  attribute float aCol;
  attribute float aBand;

  uniform float uT;
  uniform float uTime;
  uniform float uActive;
  uniform float uScale;

  varying float vBand;
  varying float vActive;

  void main() {
    // Exponential ease-out: the field arrives fast and settles softly.
    float e = 1.0 - pow(1.0 - uT, 4.0);

    vec3 pos = mix(aFrom, aTo, e);

    // While the field is still arriving it breathes; once landed the drift is
    // barely there, so the curve reads as a measurement and not as a toy.
    float idle = mix(0.055, 0.006, e);
    pos.x += sin(uTime * 0.6 + aSeed * 11.0) * idle;
    pos.y += cos(uTime * 0.5 + aSeed * 7.0) * idle;

    float isActive = (uActive >= 0.0 && abs(aCol - uActive) < 0.5) ? 1.0 : 0.0;
    vActive = isActive;
    vBand = aBand;

    // The nearest column lifts towards the reader and brightens.
    pos.z += isActive * 0.12 * e;

    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mv;

    float size = mix(1.5, 3.2, aBand) * (1.0 + isActive * 0.6);
    // Points arrive larger and settle, which reads as depth of field.
    gl_PointSize = size * uScale * mix(1.5, 1.0, e);
  }
`;

const FRAGMENT = /* glsl */ `
  /* No precision qualifier here on purpose: three.js injects the same one into
     both stages, and declaring mediump in the fragment alone made uT's
     precision differ between them, which fails to link — a scene that renders
     nothing at all with only a console line to say so. */
  uniform vec3 uAccent;
  uniform vec3 uMuted;
  uniform float uT;
  uniform float uFloor;

  varying float vBand;
  varying float vActive;

  void main() {
    // A round point with a soft edge: a mark, never a square.
    vec2 d = gl_PointCoord - vec2(0.5);
    float r = length(d) * 2.0;
    float alpha = smoothstep(1.0, 0.1, r);
    if (alpha <= 0.01) discard;

    vec3 colour = mix(uMuted, uAccent, vBand * 0.85 + vActive * 0.15);
    float strength = mix(uFloor, 1.0, vBand) * mix(0.6, 1.0, uT) + vActive * 0.3;
    gl_FragColor = vec4(colour, alpha * strength);
  }
`;

export default function HeroScene({ points, colors, blend, activeIndex, className }: HeroSceneProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<number | null>(activeIndex);

  useEffect(() => {
    activeRef.current = activeIndex;
  }, [activeIndex]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || points.length < 2) return;

    const width = mount.clientWidth || 1;
    const height = mount.clientHeight || 1;

    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, powerPreference: "low-power" });
    const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    renderer.setPixelRatio(dpr);
    renderer.setSize(width, height, false);
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    // -1..1 in both axes, which is the space the label layer is positioned in.
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 10);
    camera.position.z = 3;

    const count = Math.min(points.length * PER_POINT, MAX_POINTS);
    const from = new Float32Array(count * 3);
    const to = new Float32Array(count * 3);
    const seed = new Float32Array(count);
    const col = new Float32Array(count);
    const band = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;

      // Scattered: a loose cloud, deeper than the plane it resolves onto.
      from[i3] = (Math.random() - 0.5) * 2.6;
      from[i3 + 1] = (Math.random() - 0.5) * 2.2;
      from[i3 + 2] = (Math.random() - 0.5) * 2.2;

      // Resolved: along the measure's own curve. The parameter runs
      // continuously across the series and the height between two rows is
      // interpolated exactly as the drawn line interpolates it, so the field
      // *is* the line rather than a row of marks under it.
      const t = (i + Math.random()) / count;
      const pos = t * (points.length - 1);
      const lo = Math.floor(pos);
      const hi = Math.min(lo + 1, points.length - 1);
      const mixT = pos - lo;
      const unit = points[lo].unit * (1 - mixT) + points[hi].unit * mixT;

      const x = PLOT.left + t * (PLOT.right - PLOT.left);
      const curveY = plotY(unit);

      // Two thirds of the field crowds the curve; the rest falls away beneath
      // it so the series has volume instead of being a wire.
      const onCurve = Math.random() < 0.56;
      const fall = Math.pow(Math.random(), 1.35);
      const y = onCurve
        ? curveY + (Math.random() - 0.5) * 0.05
        : PLOT.baseline + fall * Math.max(curveY - PLOT.baseline, 0.02);
      // The band carries both brightness and size: 1 on the curve, and a
      // little more than nothing beneath it, fading towards the baseline.
      band[i] = onCurve ? 1 : 0.06 + fall * 0.3;

      to[i3] = x;
      to[i3 + 1] = y;
      to[i3 + 2] = (Math.random() - 0.5) * (onCurve ? 0.1 : 0.3);

      seed[i] = Math.random();
      col[i] = Math.round(pos);
    }

    const geometry = new THREE.BufferGeometry();
    // `position` is never read by the shader — the fly-in is a mix of aFrom and
    // aTo on the GPU — but three.js needs it to know the draw count.
    geometry.setAttribute("position", new THREE.BufferAttribute(to, 3));
    geometry.setAttribute("aFrom", new THREE.BufferAttribute(from, 3));
    geometry.setAttribute("aTo", new THREE.BufferAttribute(to, 3));
    geometry.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
    geometry.setAttribute("aCol", new THREE.BufferAttribute(col, 1));
    geometry.setAttribute("aBand", new THREE.BufferAttribute(band, 1));

    const uniforms = {
      uT: { value: 0 },
      uFloor: { value: blend === "add" ? 0.34 : 0.5 },
      uTime: { value: 0 },
      uActive: { value: -1 },
      uScale: { value: dpr },
      uAccent: { value: new THREE.Color(colors.accent) },
      uMuted: { value: new THREE.Color(colors.muted) },
    };

    const material = new THREE.ShaderMaterial({
      uniforms,
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      transparent: true,
      depthWrite: false,
      blending: blend === "add" ? THREE.AdditiveBlending : THREE.NormalBlending,
    });

    const field = new THREE.Points(geometry, material);
    scene.add(field);

    let raf: number | null = null;
    let onScreen = true;
    let elapsed = 0;
    let last = performance.now();

    const render = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      elapsed += dt;

      uniforms.uTime.value = elapsed;
      uniforms.uT.value = Math.min(elapsed / 2.4, 1);
      uniforms.uActive.value = activeRef.current ?? -1;

      renderer.render(scene, camera);
      raf = requestAnimationFrame(render);
    };

    const start = () => {
      if (raf !== null) return;
      last = performance.now();
      raf = requestAnimationFrame(render);
    };
    const stop = () => {
      if (raf === null) return;
      cancelAnimationFrame(raf);
      raf = null;
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        onScreen = entry.isIntersecting;
        if (onScreen && !document.hidden) start();
        else stop();
      },
      { threshold: 0.05 }
    );
    observer.observe(mount);

    const onVisibility = () => {
      if (document.hidden) stop();
      else if (onScreen) start();
    };
    document.addEventListener("visibilitychange", onVisibility);

    const onResize = () => {
      const w = mount.clientWidth || 1;
      const h = mount.clientHeight || 1;
      renderer.setSize(w, h, false);
    };
    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);

    return () => {
      stop();
      observer.disconnect();
      resizeObserver.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
    };
  }, [points, colors.accent, colors.muted, blend]);

  return <div ref={mountRef} aria-hidden="true" className={className} />;
}
