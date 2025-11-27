## Customer Profile Pages – SDR + Zomato

This app generates **HTML pages** that look like a dashboard:

- One page **per customer phone number** that is present in **both** files.
- A summary card with SDR details, match status, total Zomato orders, primary city, and average order value.
- A full **Zomato order history table** for that customer.

It reads directly from:

- `SDR_FILE_CLEANED.xlsx`
- `Zomato_File.xlsx`

Both files should be in the same folder as this project (your Cursor workspace: `C:\excelSort`).

The UI is built with **Flask + HTML + CSS** (no search box – just page‑by‑page navigation).

---

### 1. Install dependencies (one time)

Open a terminal in the project folder (`C:\excelSort`) and run:

```bash
pip install -r requirements.txt
```

If you have multiple Python versions, you may need to use:

```bash
python -m pip install -r requirements.txt
```

---

### 2. Run the app (Flask)

From the same folder (`C:\excelSort`), run:

```bash
python app.py
```

You should see output that includes a local address like `http://127.0.0.1:5000`. Open that URL in your browser.

---

### 3. How it works

1. The app loads both Excel files using **pandas**.
2. It normalizes the mobile numbers:
   - Keeps only digits.
   - Strips leading zeros (so `06364682957` and `6364682957` match).
3. It finds all mobile numbers that appear in **both** SDR and Zomato data.
4. For each such number, it builds a **Customer Profile Page**:
   - SDR records (present + permanent address, alternate number).
   - Zomato orders (restaurant, value, time, address, latitude/longitude).
   - Summary metrics (total orders, primary city, average order value, active/inactive).
5. You can move between customers using the **Previous/Next** buttons and page numbers at the top.

There is **no search button** – everything is precomputed and paginated for you.



