# Khoi tao database lan dau

File query khoi tao database:

```text
backend/database/init_database.sql
```

File nay tao database `rag_db` voi charset `utf8mb4`. Cac bang ung dung se duoc
backend tu tao khi start nho `models.Base.metadata.create_all(bind=engine)`.

## Chay bang MySQL client

```powershell
mysql -u root < backend/database/init_database.sql
```

Neu MySQL co mat khau:

```powershell
mysql -u root -p < backend/database/init_database.sql
```

## Sau khi tao database

Kiem tra `backend/.env` tro dung database:

```dotenv
MYSQL_URL=mysql+pymysql://root@localhost:3306/rag_db
```

Sau do start backend. Neu can tao du lieu mau/admin ban dau:

```powershell
python backend/seed.py
```
