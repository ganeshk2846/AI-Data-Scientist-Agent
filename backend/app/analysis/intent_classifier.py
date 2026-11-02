"""
backend/app/analysis/intent_classifier.py
Machine-Learning Intent & Analytical Complexity Classifier for Phase 4.
Uses scikit-learn TF-IDF + LogisticRegression with calibrated probabilities,
confidence thresholding, multi-intent ambiguity detection, and rule-assisted fallback.
Trained on multi-domain queries across E-commerce, Healthcare, Library, and Manufacturing.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, accuracy_score
from sklearn.model_selection import StratifiedKFold, train_test_split

from backend.app.analysis.contracts_v2 import (
    AnalyticalMethod,
    ComplexityLevel,
    IntentCategory,
    IntentClassificationResult,
)
from backend.app.core.logging import logger


# =====================================================================
# Multi-Domain Training Corpus (E-commerce, Healthcare, Library, Manufacturing)
# =====================================================================

TRAINING_DATA: List[Tuple[str, IntentCategory, ComplexityLevel]] = [
    # --- DESCRIPTIVE (E-commerce) ---
    ("What was our total revenue last month?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show me the gross sales by product category in 2025", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What is the average order value for delivered orders?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("List the top 10 customers by lifetime spend", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("How many orders were placed each week this quarter?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What is the return rate across different regions?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Show monthly revenue growth compared to last year", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What are the summary statistics for order amounts?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),

    # --- DESCRIPTIVE (Healthcare) ---
    ("How many patients were admitted in January?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show total billing amount by hospital department", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What is the average length of stay across wards?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("What percentage of patients were discharged within 48 hours?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Show monthly patient volume trends over the past two years", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What is the distribution of patient ages in cardiology?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("List total treatments administered by clinic location", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),

    # --- DESCRIPTIVE (University Library) ---
    ("How many books were borrowed this semester?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show the most popular book categories by loan count", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("What is the average loan duration by student major?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Show monthly checkouts across campus library branches", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("List top 5 overdue books and their borrow dates", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("What percentage of total inventory is currently checked out?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),

    # --- DESCRIPTIVE (Manufacturing) ---
    ("What was total production output yesterday?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show monthly machine operating costs across facilities", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What is the scrap rate per assembly line this quarter?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Show average cycle time across production batches", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("What is the total downtime by machine workcenter?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Display the defect distribution across product batches", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),

    # --- DIAGNOSTIC (E-commerce) ---
    ("Why did net revenue decline in Q3?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What caused the sudden increase in customer return rates?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Identify the drivers behind our gross margin drop in July", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Why are cart abandonment rates higher on mobile devices?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Detect anomalies in weekly sales over the past year", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Is there an outlier in order cancellations last Friday?", IntentCategory.DIAGNOSTIC, ComplexityLevel.MODERATE),
    ("Decompose the revenue variance between 2024 and 2025 by product category", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Investigate what caused the spike in support tickets last week", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Is there a significant correlation between discount depth and returns?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),

    # --- DIAGNOSTIC (Healthcare) ---
    ("Why did the 30-day readmission rate spike in August?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What factors drove the increase in ICU treatment costs?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Identify anomalies in patient admission rates across clinics", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Why are emergency department wait times increasing on weekends?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Is length of stay statistically correlated with patient age or diagnosis?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Decompose the increase in hospital operating expenses by ward", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Investigate why post-op infection rates differed between surgeons", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),

    # --- DIAGNOSTIC (University Library) ---
    ("Why did digital book checkouts drop sharply in October?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What factors explain the increase in overdue loans among undergraduates?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Detect anomalies in daily study room bookings during finals week", IntentCategory.DIAGNOSTIC, ComplexityLevel.MODERATE),
    ("Why did borrowing in engineering decrease while science increased?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Is there a significant difference in renewal rates between faculty and students?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),

    # --- DIAGNOSTIC (Manufacturing) ---
    ("Why did machine downtime increase significantly in Plant 2?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What are the primary drivers of batch defect rate variations?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Detect unusual temperature anomalies before the pump failure", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Investigate why production yield dropped during the night shift", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Is downtime duration correlated with maintenance delay hours?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Decompose the increase in manufacturing scrap cost by line", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),

    # --- PREDICTIVE (E-commerce) ---
    ("Forecast our sales for the next 3 months", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What will our revenue likely be next quarter?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict customer churn risk for the upcoming month", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Project product demand for the holiday season", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What is the expected order volume for the next two weeks?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict which customer segment has the highest likelihood to churn", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Forecast daily active users for next month with confidence intervals", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),

    # --- PREDICTIVE (Healthcare) ---
    ("Forecast patient admissions for the upcoming winter season", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What is the predicted ICU bed occupancy for next week?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict 30-day readmission likelihood for newly admitted patients", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Forecast emergency room arrival rates over the next 14 days", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Project expected pharmaceutical drug expenditure for next quarter", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),

    # --- PREDICTIVE (University Library) ---
    ("Forecast borrowing demand for next semester", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What is the expected book checkout volume for the midterm period?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict which library branches will experience peak study room demand", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Forecast digital collection server load for next month", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),

    # --- PREDICTIVE (Manufacturing) ---
    ("Forecast production output for the next two quarters", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict equipment failure probability over the next 100 operating hours", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Project raw material requirements for the upcoming production run", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What will machine maintenance costs be for next quarter?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Forecast energy consumption across assembly lines for next month", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),

    # --- PRESCRIPTIVE (E-commerce) ---
    ("How should we allocate our $50k marketing budget across channels to maximize revenue?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What actions should we take to reduce customer churn in at-risk segments?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),
    ("What if we increase product prices by 5%, what happens to revenue?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Simulate the impact of a 10% discount on total unit sales", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Recommend optimal reorder quantities for low-stock inventory items", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What should be our shipping strategy to minimize delivery delays?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),
    ("Optimize our pricing strategy across consumer electronics", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),

    # --- PRESCRIPTIVE (Healthcare) ---
    ("How should we reallocate nursing staff across wards to reduce overtime?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What interventions should we implement to lower readmission penalties?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),
    ("Simulate the impact on wait times if we add 2 triage nurses", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Optimize operating room scheduling to maximize daily surgeries under 40-hour constraints", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What should we do to reduce prescription drug inventory holding costs?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),

    # --- PRESCRIPTIVE (University Library) ---
    ("How should we allocate our $200k acquisition budget between print and digital books?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What policy changes should we adopt to reduce overdue loan durations?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),
    ("Simulate checkout volume if loan duration is extended from 14 to 28 days", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Recommend book reorders and retired title disposals based on circulation velocity", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),

    # --- PRESCRIPTIVE (Manufacturing) ---
    ("Optimize machine scheduling to minimize total setup and changeover downtime", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What if supplier raw material prices rise by 8%, what is the impact on batch margins?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Recommend preventive maintenance intervals to minimize unpredicted breakdowns", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("How should we allocate inventory safety stock across our 3 regional warehouses?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("How should we allocate our $30k maintenance budget across machines?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),

    # --- DESCRIPTIVE (Finance & Operations) ---
    ("What was our total cash flow from operations last quarter?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show monthly operating expenses breakdown across departments", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What is our current debt-to-equity ratio and asset turnover?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show the distribution of invoice processing times over the last 90 days", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("What were the gross profit margins by product line this fiscal year?", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),
    ("List total payroll expenditure by branch location for Q2", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("What was the average delivery lead time for domestic shipments?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Show monthly warehouse utility costs over the past 12 months", IntentCategory.DESCRIPTIVE, ComplexityLevel.MODERATE),

    # --- DIAGNOSTIC (Finance & Operations) ---
    ("Why did operating expenses surge by 20% in September?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What drove the sudden deterioration in gross profit margin?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What caused the increase in patient treatment costs between Q1 and Q2?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Why is machine downtime significantly higher during night shifts?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What are the primary drivers of book loan declines among graduate students?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Detect anomalies in invoice processing amounts and expense claims", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What is the correlation between marketing spend and customer acquisition?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Why did cash flow decrease despite revenue growth?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("What caused the sharp increase in shipping carrier surcharge fees?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),
    ("Why are customer return rates higher in the footwear category?", IntentCategory.DIAGNOSTIC, ComplexityLevel.COMPLEX),

    # --- PREDICTIVE (Finance & Operations) ---
    ("Forecast operating cash flow for the next 6 months", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What will accounts receivable likely be at the end of next quarter?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict inventory obsolescence rates for seasonal apparel", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Project hospital admission rates for the upcoming winter season", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Forecast total library checkouts for the next academic year", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What is the projected factory electricity demand for next quarter?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Forecast machine maintenance cost for the next 12 weeks", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Predict customer default probability for outstanding invoices", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("Project quarterly revenue growth across all business units", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What will hospital ICU bed occupancy likely be next week?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),

    # --- PRESCRIPTIVE (Finance & Operations) ---
    ("How should we allocate our $100k capital expenditure budget across plant upgrades?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What should we do to optimize working capital and minimize holding costs?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),
    ("Recommend budget allocation between maintenance and new machinery", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What if borrowing interest rates rise by 2%, how does our debt service coverage change?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("How should we allocate nurse shifts to minimize overtime costs?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("Recommend discount strategies to clear slow-moving inventory without eroding margins", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What actions should management take to reverse the operating margin decline?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.COMPLEX),
    ("How should we optimize inventory reorder points to reduce stockouts?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("What if supplier shipping costs increase by 15%, how should we adjust retail prices?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.MODERATE),
    ("Recommend optimal cash reserves to buffer against seasonal demand swings", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),

    # --- SQL_LOOKUP (Direct / Simple Retrieval) ---
    ("Find customer with email address sarah.connor@example.com", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("List all suppliers located in Germany", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("What is the address of warehouse 4?", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Show me the phone number for patient ID 9042", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("List all active doctors in the oncology department", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("What is the ISBN of 'Introduction to Algorithms'?", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Show the serial number for machine CNC-402", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Who is the primary contact for vendor Acme Supplies?", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Look up order details for order ID 10492", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Get book title with barcode 8839210", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Find invoice with number INV-2026-091", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("What is the tax ID for vendor Global Logistics?", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Look up employee email for staff ID 502", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Show the manufacturer part number for component X-99", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Find customer phone number for account 7721", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),
    ("Find serial number for machine CNC-101", IntentCategory.SQL_LOOKUP, ComplexityLevel.SIMPLE),

    # --- CROSS-DOMAIN UAT EXPANSIONS ---
    ("Which treatment categories are associated with increasing costs?", IntentCategory.DIAGNOSTIC, ComplexityLevel.MODERATE),
    ("Which machines contribute most to downtime?", IntentCategory.DIAGNOSTIC, ComplexityLevel.MODERATE),
    ("What factors are associated with higher defect rates?", IntentCategory.DIAGNOSTIC, ComplexityLevel.MODERATE),
    ("Which departments contribute most to budget overruns?", IntentCategory.DIAGNOSTIC, ComplexityLevel.MODERATE),
    ("Which book categories are experiencing increasing demand?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("Which product categories are experiencing increasing sales?", IntentCategory.DESCRIPTIVE, ComplexityLevel.SIMPLE),
    ("What borrowing demand should we prepare for in the next 7 days?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What maintenance trends should we expect over the next 7 days?", IntentCategory.PREDICTIVE, ComplexityLevel.ADVANCED),
    ("What resource allocation options should be evaluated?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
    ("How should the maintenance budget be allocated across machines?", IntentCategory.PRESCRIPTIVE, ComplexityLevel.ADVANCED),
]


class IntentComplexityClassifier:
    """
    Supervised Machine-Learning Intent and Analytical Complexity Classifier.
    Combines TF-IDF n-grams + Logistic Regression with rule-based boundary checks.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )
        self.intent_classifier = LogisticRegression(
            C=1.5,
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
        )
        self.complexity_classifier = LogisticRegression(
            C=1.5,
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
        )
        self.is_trained = False
        self._train_model()

    def _train_model(self):
        """Fits TF-IDF and Logistic Regression classifiers on the training corpus."""
        texts = [q[0] for q in TRAINING_DATA]
        intents = [q[1].value for q in TRAINING_DATA]
        complexities = [q[2].value for q in TRAINING_DATA]

        X = self.vectorizer.fit_transform(texts)
        self.intent_classifier.fit(X, intents)
        self.complexity_classifier.fit(X, complexities)
        self.is_trained = True
        logger.info(f"Trained IntentComplexityClassifier on {len(texts)} multi-domain examples.")

    def evaluate(self, test_size: float = 0.2, random_state: int = 42) -> Dict[str, Any]:
        """
        Evaluates classifier performance on a held-out test split using Accuracy, Precision, Recall, F1.
        """
        texts = [q[0] for q in TRAINING_DATA]
        intents = [q[1].value for q in TRAINING_DATA]

        X_train_raw, X_test_raw, y_train, y_test = train_test_split(
            texts, intents, test_size=test_size, random_state=random_state, stratify=intents
        )

        vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode", lowercase=True)
        X_train = vec.fit_transform(X_train_raw)
        X_test = vec.transform(X_test_raw)

        clf = LogisticRegression(C=1.5, class_weight="balanced", max_iter=1000, random_state=random_state)
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

        return {
            "test_sample_count": len(y_test),
            "accuracy": acc,
            "macro_precision": prec,
            "macro_recall": rec,
            "macro_f1": f1,
            "classification_report": classification_report(y_test, y_pred, zero_division=0, output_dict=True),
        }

    def classify(self, question: str) -> IntentClassificationResult:
        """
        Classifies user query into IntentCategory and ComplexityLevel.
        Detects ambiguity, low-confidence boundaries, and recommends specific analytical methods.
        """
        q_clean = question.strip()
        q_lower = q_clean.lower()

        # Deterministic hard-rule checks for high-precision syntax tokens
        # 1. Prescriptive what-if / simulation / allocation
        if any(tok in q_lower for tok in [
            "what if", "simulate", "how should we allocate", "how should the", "budget be allocated",
            "resource allocation", "allocation options", "optimize", "recommend"
        ]):
            rule_intent = IntentCategory.PRESCRIPTIVE
        # 2. Predictive forecast / prediction
        elif any(tok in q_lower for tok in [
            "forecast", "predict", "project", "expected next", "will our", "will be",
            "demand should we prepare for", "prepare for", "trends should we expect"
        ]):
            rule_intent = IntentCategory.PREDICTIVE
        # 3. Diagnostic why / cause / anomaly / drivers / contributing factors
        elif any(tok in q_lower for tok in [
            "why did", "why are", "what caused", "what drove", "drivers of", "anomalies", "outlier",
            "decompose", "associated with", "contribute most", "contributed most", "contribute to", "contributes to"
        ]):
            rule_intent = IntentCategory.DIAGNOSTIC
        # 4. Lookup / specific record query
        elif any(tok in q_lower for tok in ["find customer", "lookup", "look up", "phone number for", "email address for", "serial number for", "isbn of"]):
            rule_intent = IntentCategory.SQL_LOOKUP
        # 5. Descriptive trend / aggregation / breakdown
        elif any(tok in q_lower for tok in [
            "trend in", "monthly trend", "daily trend", "over time", "distribution of",
            "what is the average", "what was total", "what were total", "experiencing increasing", "increasing demand"
        ]):
            rule_intent = IntentCategory.DESCRIPTIVE
        else:
            rule_intent = None

        # ML Vectorization and Inference
        X = self.vectorizer.transform([q_clean])
        probs = self.intent_classifier.predict_proba(X)[0]
        classes = self.intent_classifier.classes_

        prob_dict = {cls_name: float(p) for cls_name, p in zip(classes, probs)}
        sorted_probs = sorted(prob_dict.items(), key=lambda item: item[1], reverse=True)
        top_intent_str, top_prob = sorted_probs[0]
        second_intent_str, second_prob = sorted_probs[1] if len(sorted_probs) > 1 else (None, 0.0)

        # Reconcile ML and high-confidence rule
        if rule_intent is not None:
            final_intent = rule_intent
            confidence = max(top_prob, 0.85)
        else:
            final_intent = IntentCategory(top_intent_str)
            confidence = top_prob

        # Complexity inference
        comp_probs = self.complexity_classifier.predict_proba(X)[0]
        comp_classes = self.complexity_classifier.classes_
        top_comp_str = comp_classes[np.argmax(comp_probs)]
        final_complexity = ComplexityLevel(top_comp_str)

        # Ambiguity and composite multi-intent check
        is_ambiguous = False
        requires_clarification = False
        clarification_msg = None
        is_composite = False
        composite_intents: List[IntentCategory] = []
        execution_sequence: List[str] = []

        # Check for composite multi-stage analytical requests
        has_diag_cue = any(w in q_lower for w in [
            "why did", "why are", "what caused", "what drove", "drivers of", "root cause", "decompose",
            "associated with", "contribute most", "contributed most", "contribute to", "contributes to"
        ])
        has_presc_cue = any(w in q_lower for w in [
            "what should we do", "how should we", "how can we improve", "how can we reduce", "recommend",
            "how to optimize", "how can we optimize", "optimize our", "optimize", "allocate our",
            "actions should we take", "improve it", "resource allocation",
            "allocation options", "budget be allocated", "how should the"
        ])
        has_desc_cue = any(w in q_lower for w in [
            "what was", "what were", "what happened", "sales trends", "historical", "trend in",
            "past performance", "last quarter's sales", "last quarter sales", "increasing demand",
            "experiencing increasing", "daily trend"
        ])
        has_pred_cue = any(w in q_lower for w in [
            "forecast", "predict", "project", "expected next", "what will happen", "next quarter",
            "next month", "prepare for", "demand should we prepare", "trends should we expect", "maintenance trends"
        ])

        # Check if query has competing annual timeframes or is a disjunctive either/or ambiguity
        is_annual_conflict = "last year" in q_lower and "next year" in q_lower
        is_disjunctive_ambiguity = " or " in q_lower and any(w in q_lower for w in ["past", "historical"]) and any(w in q_lower for w in ["future", "forecast"])

        if is_annual_conflict or is_disjunctive_ambiguity:
            is_ambiguous = True
            requires_clarification = True
            clarification_msg = (
                "Your question asks whether to evaluate historical figures or future forecasts. "
                "Please specify whether you would like historical descriptive analysis or a future predictive forecast."
            )
        else:
            # Multi-stage composition detection
            if has_diag_cue and has_pred_cue and has_presc_cue:
                is_composite = True
                composite_intents = [IntentCategory.DIAGNOSTIC, IntentCategory.PREDICTIVE, IntentCategory.PRESCRIPTIVE]
                execution_sequence = ["diagnostic_driver_analysis", "predictive_forecasting", "prescriptive_recommendations"]
            elif has_diag_cue and has_presc_cue:
                is_composite = True
                composite_intents = [IntentCategory.DIAGNOSTIC, IntentCategory.PRESCRIPTIVE]
                execution_sequence = ["diagnostic_driver_analysis", "prescriptive_recommendations"]
            elif has_desc_cue and has_pred_cue:
                is_composite = True
                composite_intents = [IntentCategory.DESCRIPTIVE, IntentCategory.PREDICTIVE]
                execution_sequence = ["descriptive_trend_analysis", "predictive_forecasting"]
            elif has_desc_cue and has_diag_cue:
                is_composite = True
                composite_intents = [IntentCategory.DESCRIPTIVE, IntentCategory.DIAGNOSTIC]
                execution_sequence = ["descriptive_trend_analysis", "diagnostic_driver_analysis"]
            elif has_pred_cue and has_presc_cue:
                is_composite = True
                composite_intents = [IntentCategory.PREDICTIVE, IntentCategory.PRESCRIPTIVE]
                execution_sequence = ["predictive_forecasting", "prescriptive_recommendations"]

            if is_composite:
                final_intent = composite_intents[0]
                final_complexity = ComplexityLevel.ADVANCED
                confidence = max(confidence, 0.90)

        # Low confidence fallback check
        if confidence < 0.28 and not rule_intent and not is_composite:
            is_ambiguous = True
            final_intent = IntentCategory.SQL_LOOKUP
            final_complexity = ComplexityLevel.SIMPLE

        # Map intent to recommended analytical methods
        methods = self._map_methods(final_intent, final_complexity, q_lower)

        return IntentClassificationResult(
            primary_intent=final_intent,
            complexity=final_complexity,
            confidence_score=round(float(confidence), 3),
            all_probabilities={k: round(v, 4) for k, v in prob_dict.items()},
            is_ambiguous=is_ambiguous,
            requires_clarification=requires_clarification,
            suggested_clarification=clarification_msg,
            recommended_methods=methods,
            is_composite=is_composite,
            composite_intents=composite_intents,
            execution_sequence=execution_sequence,
        )

    def _map_methods(
        self, intent: IntentCategory, complexity: ComplexityLevel, query_lower: str
    ) -> List[AnalyticalMethod]:
        """Maps classified intent and query text to candidate analytical methods."""
        if intent == IntentCategory.DESCRIPTIVE:
            if any(w in query_lower for w in ["trend", "monthly", "daily", "growth", "over time"]):
                return [AnalyticalMethod.TREND_ANALYSIS, AnalyticalMethod.PERIOD_OVER_PERIOD]
            if any(w in query_lower for w in ["compare", "versus", "vs", "difference"]):
                return [AnalyticalMethod.PERIOD_OVER_PERIOD, AnalyticalMethod.SEGMENTATION]
            if any(w in query_lower for w in ["distribution", "summary", "statistics", "stats"]):
                return [AnalyticalMethod.DESCRIPTIVE_STATS, AnalyticalMethod.METRIC_AGGREGATION]
            return [AnalyticalMethod.METRIC_AGGREGATION, AnalyticalMethod.SEGMENTATION]

        elif intent == IntentCategory.DIAGNOSTIC:
            methods = []
            if any(w in query_lower for w in ["anomaly", "outlier", "spike", "drop", "unusual"]):
                methods.append(AnalyticalMethod.ANOMALY_DETECTION)
            if any(w in query_lower for w in ["why", "driver", "caused", "decompose", "variance"]):
                methods.append(AnalyticalMethod.VARIANCE_DECOMPOSITION)
            if any(w in query_lower for w in ["correlation", "correlated", "relationship", "difference between"]):
                methods.append(AnalyticalMethod.STATISTICAL_CORRELATION)
                methods.append(AnalyticalMethod.HYPOTHESIS_TESTING)
            return methods or [AnalyticalMethod.VARIANCE_DECOMPOSITION, AnalyticalMethod.ANOMALY_DETECTION]

        elif intent == IntentCategory.PREDICTIVE:
            if any(w in query_lower for w in ["forecast", "month", "quarter", "season", "volume"]):
                return [AnalyticalMethod.TIME_SERIES_FORECAST]
            if any(w in query_lower for w in ["churn", "probability", "classify", "likelihood"]):
                return [AnalyticalMethod.SUPERVISED_CLASSIFICATION, AnalyticalMethod.SUPERVISED_REGRESSION]
            return [AnalyticalMethod.TIME_SERIES_FORECAST]

        elif intent == IntentCategory.PRESCRIPTIVE:
            if any(w in query_lower for w in ["allocate", "budget", "optimize", "maximize", "minimize"]):
                return [AnalyticalMethod.CONSTRAINED_OPTIMIZATION]
            if any(w in query_lower for w in ["what if", "simulate", "shock", "increase by", "discount"]):
                return [AnalyticalMethod.WHAT_IF_SCENARIO]
            return [AnalyticalMethod.WHAT_IF_SCENARIO, AnalyticalMethod.CONSTRAINED_OPTIMIZATION]

        return [AnalyticalMethod.SQL_QUERY_ONLY]


# Singleton instance
intent_classifier = IntentComplexityClassifier()

