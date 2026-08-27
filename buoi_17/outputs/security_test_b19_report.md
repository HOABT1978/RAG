# BÁO CÁO KIỂM THỬ AN TOÀN VÀ PHÂN QUYỀN (SECURITY & GUARDRAIL TEST REPORT) - BUỔI 19

Báo cáo này ghi nhận kết quả kiểm thử an toàn bảo mật, phân quyền RBAC và khả năng tự chủ offline của hệ thống trợ lý kiểm toán AI (Buổi 19).

---

## 1. Kết Quả 6 Hạng Mục Kiểm Tra An Toàn

### Hạng mục 1: **Local Offline Privacy Check**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > LLM_PROVIDER is correctly set to 'ollama' in .env. Ollama Base URL is configured to: http://localhost:11434. All queries are routed locally to the containerized service and no external API keys/prompts are sent to internet LLM endpoints.

---
### Hạng mục 2: **RBAC Enforcement**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > RBAC pre-filtering successfully blocked 'Staff' role from accessing restricted CAR policy chunks (agr_car02).

---
### Hạng mục 3: **Citation Integrity**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > Citations verified in conflicts CSV (9 rows). Citations verified in checklist CSV (3 rows). Citations verified in gap CSV (5 rows).

---
### Hạng mục 4: **Human Review Guardrail**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > 100% of generated records in conflicts, checklists, and gap analysis results have 'review_status' set to 'NEEDS_HUMAN_REVIEW' forcing manual audit verification.

---
### Hạng mục 5: **Audit Log Privacy**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > Scanned audit log file. All keys containing 'key', 'secret', or 'password' are correctly masked with '[REDACTED]'.

---
### Hạng mục 6: **Local Model Resilience**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > System maintains local model resilience. Offline requests successfully execute via the local Ollama container or trigger the safe rule-engine fallback instead of crashing.

---

## 2. Kết Luận Nghiệm Thu Bảo Mật

```text
SECURITY & GUARDRAIL TESTS: PASS
```
