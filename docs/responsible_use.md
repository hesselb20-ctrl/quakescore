# Responsible use

A QuakeScore is risk information from a statistical screening layer. It is not an engineering
assessment, not a safety certificate and not a condemnation notice. This document sets the rules for
how scores are shown, what a high-risk finding triggers, and what the product never says.
Time periods marked ASSUMED are placeholders to be set by policy.

## 1. Uncertainty comes with every score

- A score is never shown without its 5-95% band and its provenance label (`REAL`, `SIM`, `REF`,
  `ASSUMED`). The API, dashboard and exports enforce this; a score without both is a defect.
- The score is a relative screening measure. The fragility adjustment is physics-based and has not
  been calibrated against observed damage (`DESIGN.md` section 6).
- Buildings below the contributor and session thresholds get "needs data", not a score.
- Class ambiguity is shown. If the structural class is uncertain, the class distribution is shown
  with the score.

## 2. What a high-risk anomaly triggers

A flag is raised only when the building is anomalous under every plausible structural class, for
example a much lower stiffness than expected for its class and height. A flag is a prompt to look, not
a finding of defect. The steps, in order:

1. **Internal check.** Re-run identification, check for artefacts and sensor faults, and check change
   detection for a recent shift. A flag that does not survive this goes no further.
2. **Notice to contributor residents first.** The people whose phones produced the data are told
   before any buyer. The notice is in plain language: what was measured, what looked unusual, what it
   does and does not mean, and what to do next. It does not use the words "unsafe" or "dangerous".
   Contributors can also be pseudonymous, so the notice goes through the app.
3. **Route to an engineer's inspection.** The notice explains that only a qualified structural
   engineer can assess a building, how to commission an inspection through a local professional body or
   the owner's own engineer, and what to ask for. The product does not choose or recommend a named
   firm, and does not pay for inspections unless a separate policy says so. Where a building is a
   public hazard in the opinion of an engineer, the engineer's own duties apply; the product does not
   substitute for them.
4. **Owner notification.** The building owner or manager, where identifiable, receives the same
   explanation and the same route.
5. **Hold period before the score reaches insurers.** The score is withheld from buyers for a hold
   period (ASSUMED, length to be set) so that residents and owners can respond. The hold can be
   extended while an inspection is under way.
6. **Appeal and correction.** An owner can contest a score, supply evidence (an engineer's report,
   retrofit records, drawings), and ask for re-evaluation. A corrected or withdrawn score replaces the
   old one in all deliveries, and buyers are notified. Appeals are logged with outcome and timing.

## 3. Misuse risks and the rules that mitigate them

| Risk | Product rules |
|---|---|
| Premium discrimination against already-vulnerable neighbourhoods | Data is sold at building level with bands, not as a neighbourhood ranking. Contracts forbid area-level pricing derived from scores. Coverage and score distributions are audited by area for systematic skew. Scores are not used for decline-to-cover decisions, only as one input |
| Redlining by proxy (the score tracks building age, tenure or income) | Report how far scores correlate with age, material and area. Contracts require the buyer to document how scores enter decisions. Sale is refused where the stated use is exclusion of an area |
| False reassurance from a good score | A good score says "no anomaly seen in the measured mode", not "safe". The band and the standing statement in section 4 are always shown. Many failure modes (soft storey, detailing, foundation, non-structural damage) are not visible in a first-mode frequency |
| Panic from a bad score | Residents are told first, in plain language, with a route to inspection (section 2). No public map shows individual building scores. Public coverage maps show "needs data" or coverage only |
| Liability if a score is wrong | Scores are contractually information, not advice, with the limits in section 1. The audit trail keeps inputs, versions and provenance for every score. Appeals and corrections are propagated. Legal review of liability and insurance for the company is open |
| Re-identification of a household through a small-building score | K-threshold and the limits in `docs/privacy.md` section 5 |
| Use of `SIM` or `ASSUMED` values as if measured | Provenance travels with every value. Deliveries containing non-`REAL` values state it. Nothing is called `REAL` until it comes from the field protocol (`docs/validation_protocol.md`) |

## 4. What the product must never say

- That a building is safe, unsafe, sound, dangerous, compliant, or "will" or "will not" survive an
  earthquake.
- That a score is an engineering assessment, certificate, inspection, code check or rating by an
  engineer.
- That a low score means a building should be vacated or not insured, or that a high score means no
  inspection is needed.
- A score without its band and provenance label, or for a building below the thresholds.
- That the method is validated against building damage. It is not; see `DESIGN.md` section 9.
- That an academic group endorses the product, or that any group lists insurance as an application
  (unverified; see `docs/references.md`).
- Any claim of regulatory compliance in any country (see `docs/privacy.md`).

Standing statement shown with every score: "This is a statistical screening estimate with stated
uncertainty. It is not an engineering assessment. Only a qualified structural engineer can assess a
building."

## 5. Open items

Hold period length; who funds any inspection; enforcement of the area-pricing ban; local rules on
telling residents and owners; professional liability cover.
