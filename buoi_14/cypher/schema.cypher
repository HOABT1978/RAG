// Thiết lập ràng buộc khóa duy nhất cho các node trong Đồ thị tri thức (Buổi 14)

CREATE CONSTRAINT unique_vanban_id IF NOT EXISTS
FOR (v:VanBan) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT unique_dieukhoan_id IF NOT EXISTS
FOR (d:DieuKhoan) REQUIRE d.id IS UNIQUE;
