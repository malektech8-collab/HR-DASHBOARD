# Stakeholder Review Guide

This guide assists stakeholders in evaluating the Governance Command Center while ensuring alignment with security policies.

## 1. What to Look For in the Command Center
- **The Dashboard UI**: Review the mock department headcount, payroll run trends, and attrition rates. Note that all of these values are synthetic.
- **The Governance Widget**: Located on the main page, this widget displays the active status of the validation gates.

## 2. Understanding the Governance Locks
To protect real employee data, the application uses a strict three-key lock mechanism:
- **CHRO Executive Lock**: Represents corporate leadership alignment.
- **CISO Cyber Lock**: Represents security review and token issuance.
- **IT Ops Deployment Lock**: Represents infrastructure confirmation.

```
+------------------------------------------+
|          GOVERNANCE STATUS               |
|                                          |
|  [HOLD] CHRO Executive Approval          |
|  [HOLD] CISO Cyber Approval              |
|  [HOLD] IT Ops Deployment Approval       |
+------------------------------------------+
|  RESULT: SYSTEM LOCKED (SYNTHETIC MODE)  |
+------------------------------------------+
```

## 3. Why the Decision Remains "Hold"
The current build is for layout, schema, and local validation testing. Because we have no authorization to inspect or process actual employee databases, the system is hardcoded to remain locked. No production credentials or pipelines have been designed or implemented.
