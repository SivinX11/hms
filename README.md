## Run locally

From the `hms` folder:

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

pip install -r requirements.txt

python app.py
```

Open:

- Register: `http://127.0.0.1:5000/auth/register`
- Login: `http://127.0.0.1:5000/auth/login`
