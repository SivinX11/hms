## Run locally

From the `hms` folder:

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

pip install -r requirements.txt
```

### Initialize DB

```bash
python sql_init.py
```

### Run Server

```bash
python app.py
```

Open:

- Register: `http://127.0.0.1:5000/auth/register`
- Login: `http://127.0.0.1:5000/auth/login`

## Sample data

To create tables and load sample users, doctors, patients and appointments:

```bash
python3 sql_init.py
python3 seed_sample_data.py
```

Default admin login after seeding:
- Email: `admin@hms.com`
- Password: `Password@123`

The seed script also creates 2 doctors and 3 patients using the same password.
