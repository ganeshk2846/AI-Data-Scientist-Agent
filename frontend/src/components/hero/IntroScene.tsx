"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * The opening sequence's point field.
 *
 * The same material as the hero's field, doing the opening's job: a cloud
 * assembles out of the dark and gathers into the rule beneath the wordmark,
 * then releases upward as the overlay lifts and hands the screen to the
 * product — where the identical material becomes the warehouse's own curve.
 *
 * It shows no number, which is the whole reason it is allowed to be a shape
 * rather than a series: the moment a mark on screen stands for a value, it
 * comes from the API. See frontend/DESIGN.md §8b.
 *
 * Everything moves in the vertex shader, so the sequence costs two uniform
 * writes and one draw call per frame while the rest of the app mounts and its
 * opening query is already in flight behind the overlay.
 */

interface IntroSceneProps {
  colors: { accent: string; muted: string };
  /** True once the overlay starts to lift: the field lets go with it. */
  release: boolean;
  /** Where the rule sits, as a fraction of the viewport height from the top. */
  anchor: number;
  className?: string;
}

const COUNT = 3600;

const VERTEX = /* glsl */ `
  attribute vec3 aFrom;
  attribute vec3 aTo;
  attribute float aSeed;

  uniform float uT;
  uniform float uTime;
  uniform float uRelease;
  uniform float uScale;

  varying float vSeed;

  void main() {
    vSeed = aSeed;
    float e = 1.0 - pow(1.0 - uT, 3.0);
    vec3 pos = mix(aFrom, aTo, e);

    // Still moving while it gathers, almost still once it has.
    float idle = mix(0.08, 0.004, e);
    pos.x += sin(uTime * 0.7 + aSeed * 13.0) * idle;
    pos.y += cos(uTime * 0.55 + aSeed * 9.0) * idle;

    // The release: the field lets go upward as the overlay lifts.
    pos.y += uRelease * (0.25 + aSeed * 0.75);
    pos.x += uRelease * (aSeed - 0.5) * 0.5;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = mix(3.4, 1.9, e) * uScale;
  }
`;

const FRAGMENT = /* glsl */ `
  uniform vec3 uAccent;
  uniform vec3 uMuted;
  uniform float uT;
  uniform float uRelease;

  varying float vSeed;

  void main() {
    vec2 d = gl_PointCoord - vec2(0.5);
    float alpha = smoothstep(1.0, 0.1, length(d) * 2.0);
    if (alpha <= 0.01) discard;

    vec3 colour = mix(uMuted, uAccent, vSeed);
    float strength = mix(0.35, 0.95, uT) * (1.0 - uRelease * 1.6);
    gl_FragColor = vec4(colour, alpha * max(strength, 0.0));
  }
`;

export default function IntroScene({ colors, release, anchor, className }: IntroSceneProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const releaseRef = useRef(0);

  // The release is driven here rather than inside the render loop's closure,
  // so it can start from a prop without tearing the scene down and rebuilding
  // every buffer mid-sequence.
  useEffect(() => {
    if (!release) return;
    let frame = 0;
    const start = performance.now();
    const step = () => {
      const t = Math.min((performance.now() - start) / 500, 1);
      releaseRef.current = t;
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [release]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

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
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 10);
    camera.position.z = 3;

    // The rule the field gathers into, in the same -1..1 space the overlay's
    // own layout is measured in.
    const ruleY = 1 - anchor * 2;

    const from = new Float32Array(COUNT * 3);
    const to = new Float32Array(COUNT * 3);
    const seed = new Float32Array(COUNT);

    for (let i = 0; i < COUNT; i++) {
      const i3 = i * 3;
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.7 + Math.random() * 1.6;

      from[i3] = Math.cos(angle) * radius;
      from[i3 + 1] = Math.sin(angle) * radius * 0.8;
      from[i3 + 2] = (Math.random() - 0.5) * 2;

      // A rule: dense in the middle, thinning towards both ends.
      const t = Math.random();
      const eased = Math.sign(t - 0.5) * Math.pow(Math.abs(t - 0.5) * 2, 0.7) * 0.5;
      to[i3] = eased * 1.52;
      to[i3 + 1] = ruleY + (Math.random() - 0.5) * 0.035;
      to[i3 + 2] = (Math.random() - 0.5) * 0.1;

      seed[i] = Math.random();
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(to, 3));
    geometry.setAttribute("aFrom", new THREE.BufferAttribute(from, 3));
    geometry.setAttribute("aTo", new THREE.BufferAttribute(to, 3));
    geometry.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));

    const uniforms = {
      uT: { value: 0 },
      uTime: { value: 0 },
      uRelease: { value: 0 },
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
      blending: THREE.AdditiveBlending,
    });

    const field = new THREE.Points(geometry, material);
    scene.add(field);

    let raf: number | null = null;
    let elapsed = 0;
    let last = performance.now();

    const render = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      elapsed += dt;
      uniforms.uTime.value = elapsed;
      uniforms.uT.value = Math.min(elapsed / 1.5, 1);
      uniforms.uRelease.value = releaseRef.current;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(render);
    };
    raf = requestAnimationFrame(render);

    const onResize = () => {
      renderer.setSize(mount.clientWidth || 1, mount.clientHeight || 1, false);
    };
    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);

    return () => {
      if (raf !== null) cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
    };
  }, [colors.accent, colors.muted, anchor]);

  return <div ref={mountRef} aria-hidden="true" className={className} />;
}
