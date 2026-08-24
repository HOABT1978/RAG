# BÁO CÁO KIỂM THỬ BẢO MẬT & KIỂM SOÁT (SECURITY & GUARDRAIL TEST REPORT) - BUỔI 18

Báo cáo này ghi nhận kết quả kiểm thử bảo mật, phân quyền RBAC và kiểm soát dữ liệu trên ứng dụng AI Compliance & Audit Assistant (Buổi 18).

---

## 1. Kết Quả Chi Tiết 7 Bài Kiểm Thử

### Bài test 1: **RBAC Test**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > Role 'Staff' successfully blocked from accessing 'Risk_Manager'/'Admin' restricted document 'agr_car02'.

---
### Bài test 2: **Citation Integrity**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > All conflicts have valid citations (2 items checked). All checklist items have valid source_citations (4 items checked).

---
### Bài test 3: **Hallucination Check**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > All citations and Document IDs exist in the master combined dataset. No hallucinated metadata detected.

---
### Bài test 4: **Human Review Guardrail**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > All conflict rows have NEEDS_HUMAN_REVIEW status. All checklist rows have NEEDS_HUMAN_REVIEW status.

---
### Bài test 5: **Audit Log Privacy**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > Audit log scanned. All sensitive fields containing 'key', 'password', or 'secret' are successfully masked with '[REDACTED]'.

---
### Bài test 6: **Unknown Domain Test**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > Unknown domain query handled gracefully. Retrieved candidates have low semantic match score and no false citations were generated.

---
### Bài test 7: **File Export Verification**
* **Trạng thái**: ✅ PASS
* **Mô tả kết quả**:
  > Conflicts CSV has valid schema and 2 entries. Checklist CSV has valid schema and 4 entries. 

---

## 2. Kết Luận Nghiệm Thu Bảo Mật

```text
SECURITY & GUARDRAIL TESTS: PASS
```
