from database.db_config import SessionLocal, engine
from database import models
from services.auth.auth_service import get_password_hash

def seed_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # If users already present, skip seeding users but still ensure departments exist.
    try:
        def get_or_create_department(name: str):
            dept = db.query(models.Department).filter(models.Department.name == name).one_or_none()
            if dept:
                return dept
            dept = models.Department(name=name)
            db.add(dept)
            db.flush()  # populate dept.id
            return dept

        # Ensure departments exist (id will be assigned by DB)
        d0 = get_or_create_department("Admin")
        d1 = get_or_create_department("Hành Chính Nhân Sự")
        d2 = get_or_create_department("Kế Toán")
        d3 = get_or_create_department("Công Nghệ Thông Tin")
        db.commit()

        if db.query(models.User).first():
            print("Dữ liệu seed đã tồn tại. Bỏ qua tạo user.")
            db.close()
            return

        admin = models.User(username="admin", hashed_password=get_password_hash("admin123"), full_name="Quản trị viên", role="admin", department_id=d0.id)
        manager = models.User(username="tp_nhansu", hashed_password=get_password_hash("manager123"), full_name="Trưởng phòng NS", role="manager", department_id=d1.id)
        employee = models.User(username="nv_ketoan", hashed_password=get_password_hash("nv123"), full_name="Nhân viên KT", role="employee", department_id=d2.id)

        db.add_all([admin, manager, employee])
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    t1 = models.Tag(name="Tài chính")
    t2 = models.Tag(name="Nhân sự")
    t3 = models.Tag(name="Quy trình")
    db.add_all([t1, t2, t3])
    db.commit()

    print("Seed thành công!")
    print("  admin / admin123")
    print("  tp_nhansu / manager123")
    print("  nv_ketoan / nv123")
    db.close()

if __name__ == "__main__":
    seed_data()
