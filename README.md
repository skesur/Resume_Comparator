# ⚡ RESUME_COMPARATOR // AI & ML Match Engine

An AI-powered web application that analyzes and matches PDF resumes against job posting criteria using pre-trained Natural Language Processing (NLP) deep learning models. Wrapped in a responsive, high-fidelity dark Cyberpunk user interface.

---

## 🚀 Key Features

* **Pre-trained Deep Learning Embeddings**: Utilizes the `all-MiniLM-L6-v2` Sentence-Transformer model (~90MB, 384-dimensional dense vectors) to compute semantic context similarity between the resume and job requirements.
* **Warm Singleton preloader**: Auto-loads the transformer model on server startup, keeping subsequent request response times under **100ms** on CPU.
* **Dual-Engine Fail-safe**: Automatic fallback to local `TfidfVectorizer` (TF-IDF + Cosine Similarity) if the deep learning model encounters system constraints.
* **4-Category Analytical Assessment**:
  1. **Resume Skills Match**: Direct token checks combined with semantic vector mapping.
  2. **Experience Understanding**: Captures work duration declarations and computes dates/ranges dynamically.
  3. **Project Portfolio Relevance**: Isolates projects section and analyzes context relevance to target role.
  4. **Education Checking**: Maps qualifications (Bachelor's, Master's, PhD, etc.) against job criteria.
* **Cyberpunk Dashboard UI**: Interactive results featuring overall score indicators, a responsive **Chart.js Radar Graph**, breakdown lists, and expandable metrics accordions.
* **Stage-Progress Loader**: Visual progressive loader tracking text parsing, embedding calculations, and database commits.
* **Mobile-Responsive**: Tailored CSS grids and breakpoints ensuring a seamless experience across phones, tablets, and desktops.
* **100% Offline & Private**: Zero external API calls—all calculations run locally on your system.

---

## 🛠️ Tech Stack

* **Backend**: Django 6.x, SQLite
* **Machine Learning / NLP**: PyTorch, Sentence-Transformers, Scikit-Learn, NLTK, NumPy, PyPDF
* **Frontend**: HTML5, CSS3, Vanilla JS, Bootstrap 5, FontAwesome, Chart.js

---

## 📦 Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.10+** installed. Clone this repository and navigate to the project directory:
```bash
git clone https://github.com/your-username/resume_comparator.git
cd resume_comparator
```

### 2. Install Dependencies
Install the required packages using `pip`:
```bash
pip install -r requirements.txt
```
*(Note: Installing `sentence-transformers` will automatically install `torch` and `transformers` as core requirements.)*

### 3. Run Migrations
Run standard Django migrations to set up the SQLite database:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Boot the Server
Start the development server:
```bash
python manage.py runserver
```
*(Note: The server will display `--- PRE-LOADING EMBEDDING MODEL START ---` on startup. On its first boot, it will automatically download the lightweight ~90MB transformer model from the Hugging Face Hub, which may take a minute. Subsequent boot times and resume matches will be instant.)*

Open your browser and navigate to **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** to start matching!

---

## 🧪 Running Automated Tests

Run the Django test suite to verify the NLP matching models and HTTP routes:
```bash
python manage.py test comparator
```

---

## 🔒 Privacy & Security
This application is fully privacy-focused. Candidate resumes and job posting forms are stored locally on your server. No resume data or job descriptions are transmitted to third-party endpoints.
