from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for, send_from_directory
import re
import json
import io
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'resume_analyzer_secret_key_2026'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

DB_NAME = "resume_analyzer.db"

# ─────────────────────────────────────────────
# Job Role Skill Sets
# ─────────────────────────────────────────────
JOB_ROLES = {
    "Data Scientist": [
        "python", "machine learning", "deep learning", "statistics", "numpy", "pandas",
        "scikit-learn", "tensorflow", "keras", "data visualization", "matplotlib",
        "seaborn", "sql", "r", "jupyter", "scipy", "feature engineering",
        "neural networks", "nlp", "big data"
    ],
    "Data Analyst": [
        "sql", "excel", "python", "tableau", "power bi", "data visualization",
        "pandas", "numpy", "statistics", "r", "data cleaning", "reporting",
        "google analytics", "looker", "etl", "data warehousing", "business intelligence",
        "pivot tables", "vlookup", "mysql"
    ],
    "AI Engineer": [
        "python", "deep learning", "tensorflow", "pytorch", "neural networks",
        "nlp", "computer vision", "machine learning", "transformers", "bert",
        "llm", "cuda", "gpu programming", "model deployment", "mlops",
        "hugging face", "openai", "langchain", "rag", "vector database"
    ],
    "Machine Learning Engineer": [
        "python", "machine learning", "scikit-learn", "tensorflow", "pytorch",
        "feature engineering", "model deployment", "mlops", "docker", "kubernetes",
        "aws", "gcp", "azure", "spark", "hadoop", "sql", "statistics",
        "a/b testing", "ci/cd", "flask"
    ],
    "Web Developer": [
        "html", "css", "javascript", "react", "nodejs", "sql", "mongodb",
        "python", "php", "mysql", "git", "rest api", "typescript",
        "bootstrap", "jquery", "webpack", "express", "vue", "angular", "tailwind"
    ],
    "Frontend Developer": [
        "html", "css", "javascript", "react", "typescript", "vue", "angular",
        "tailwind", "bootstrap", "sass", "webpack", "git", "figma", "responsive design",
        "redux", "next.js", "jest", "cypress", "accessibility", "ui/ux"
    ],
    "Backend Developer": [
        "python", "java", "nodejs", "sql", "mongodb", "postgresql", "mysql",
        "rest api", "graphql", "docker", "kubernetes", "aws", "git", "flask",
        "django", "spring", "express", "redis", "microservices", "ci/cd"
    ],
    "Software Developer": [
        "python", "java", "c++", "c#", "javascript", "git", "sql", "oop",
        "data structures", "algorithms", "design patterns", "agile", "scrum",
        "unit testing", "rest api", "docker", "linux", "debugging", "code review", "github"
    ],
    "DevOps Engineer": [
        "docker", "kubernetes", "aws", "azure", "gcp", "linux", "bash",
        "terraform", "ansible", "jenkins", "ci/cd", "git", "python",
        "monitoring", "prometheus", "grafana", "nginx", "networking", "security", "helm"
    ],
    "Database Administrator": [
        "sql", "mysql", "postgresql", "oracle", "mongodb", "sql server",
        "database design", "indexing", "backup", "performance tuning", "replication",
        "redis", "cassandra", "data modeling", "etl", "stored procedures",
        "triggers", "views", "normalization", "database security"
    ],
    "Cloud Engineer": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "linux",
        "networking", "security", "storage", "serverless", "lambda",
        "s3", "ec2", "cloud architecture", "devops", "python", "bash", "iam", "vpc"
    ],
    "Cybersecurity Analyst": [
        "networking", "security", "penetration testing", "linux", "python",
        "firewalls", "encryption", "siem", "vulnerability assessment", "ethical hacking",
        "nmap", "wireshark", "metasploit", "soc", "incident response",
        "compliance", "risk assessment", "bash", "forensics", "owasp"
    ]
}

ALL_SKILLS = sorted(list(set(skill for skills in JOB_ROLES.values() for skill in skills)))

RESUME_SECTIONS = {
    "email": [r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"],
    "phone": [r"\+?\d[\d\s\-]{8,}\d"],
    "education": [r"\beducation\b", r"\bacademic\b", r"\bqualification\b"],
    "skills": [r"\bskills\b", r"\btechnical skills\b", r"\bcore competencies\b"],
    "projects": [r"\bprojects\b", r"\bproject\b"],
    "experience": [r"\bexperience\b", r"\bwork experience\b", r"\binternship\b"],
    "certifications": [r"\bcertifications\b", r"\bcertification\b", r"\blicenses\b"],
    "linkedin": [r"linkedin\.com", r"\blinkedin\b"],
    "github": [r"github\.com", r"\bgithub\b"],
    "summary": [r"\bsummary\b", r"\bobjective\b", r"\bprofile\b"]
}

ACTION_VERBS = [
    "developed", "built", "designed", "implemented", "created", "optimized",
    "analyzed", "led", "managed", "improved", "automated", "deployed",
    "engineered", "integrated", "collaborated", "delivered"
]

WEAK_PHRASES = [
    "worked on", "responsible for", "helped with", "involved in", "participated in"
]

INTERVIEW_QUESTION_BANK = {
    "python": [
        "Explain the difference between a list and a tuple in Python.",
        "What are Python decorators and where would you use them?"
    ],
    "sql": [
        "What is the difference between WHERE and HAVING in SQL?",
        "Write a query to find the second highest salary from an employee table."
    ],
    "javascript": [
        "Explain the difference between let, const, and var.",
        "What is the difference between == and === in JavaScript?"
    ],
    "react": [
        "What is the difference between props and state in React?",
        "What is the purpose of useEffect in React?"
    ],
    "machine learning": [
        "What is overfitting in machine learning and how do you reduce it?",
        "Explain the difference between supervised and unsupervised learning."
    ],
    "docker": [
        "What is the difference between a Docker image and a Docker container?",
        "Why is Docker useful in deployment workflows?"
    ],
    "aws": [
        "What is the difference between EC2 and S3?",
        "How would you deploy a simple web app on AWS?"
    ],
    "data structures": [
        "When would you use a hash map over an array?",
        "Explain the difference between stack and queue with examples."
    ],
    "algorithms": [
        "What is time complexity and why is Big-O notation important?",
        "Explain the difference between linear search and binary search."
    ],
    "rest api": [
        "What are common HTTP methods used in REST APIs?",
        "What is the difference between PUT and PATCH?"
    ],
    "linux": [
        "What is the difference between a process and a thread in Linux?",
        "Which Linux commands do you use most often for debugging?"
    ]
}

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            best_role TEXT,
            ats_score REAL,
            target_role TEXT,
            target_role_score REAL,
            jd_match_score REAL,
            created_at TEXT,
            result_json TEXT
        )
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# File Text Extraction
# ─────────────────────────────────────────────
def extract_text_from_pdf(file):
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception:
        return ""


def extract_text_from_docx(file):
    try:
        import docx
        doc = docx.Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception:
        return ""


# ─────────────────────────────────────────────
# Text Analysis Helpers
# ─────────────────────────────────────────────
def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_skills(text):
    text_lower = text.lower()
    detected = []
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            detected.append(skill)
    return sorted(list(set(detected)))


def calculate_match(detected_skills, role_skills):
    if not role_skills:
        return 0
    detected_lower = [s.lower() for s in detected_skills]
    matched = sum(1 for skill in role_skills if skill.lower() in detected_lower)
    return round((matched / len(role_skills)) * 100, 1)


def get_missing_skills(detected_skills, role_skills):
    detected_lower = {s.lower() for s in detected_skills}
    missing = [skill for skill in role_skills if skill.lower() not in detected_lower]
    return sorted(missing)


def check_resume_sections(text):
    text_lower = text.lower()
    result = {}
    for section, patterns in RESUME_SECTIONS.items():
        result[section] = any(re.search(pattern, text_lower) for pattern in patterns)
    return result


def section_score(section_status):
    total = len(section_status)
    present = sum(1 for v in section_status.values() if v)
    return present, total, round((present / total) * 100, 1) if total else 0


def keyword_frequency(text, keywords):
    text_lower = text.lower()
    counts = {}
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        counts[keyword] = len(re.findall(pattern, text_lower))
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def analyze_job_description(jd_text, detected_skills):
    if not jd_text.strip():
        return {
            "jd_match_score": 0,
            "jd_detected_keywords": [],
            "jd_missing_keywords": [],
            "jd_keyword_frequency": {}
        }

    jd_text_lower = jd_text.lower()
    jd_keywords = []

    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, jd_text_lower):
            jd_keywords.append(skill)

    jd_keywords = sorted(list(set(jd_keywords)))
    detected_lower = {s.lower() for s in detected_skills}

    matched = [skill for skill in jd_keywords if skill.lower() in detected_lower]
    missing = [skill for skill in jd_keywords if skill.lower() not in detected_lower]

    score = round((len(matched) / len(jd_keywords)) * 100, 1) if jd_keywords else 0
    freq = keyword_frequency(jd_text, jd_keywords)

    return {
        "jd_match_score": score,
        "jd_detected_keywords": matched,
        "jd_missing_keywords": missing,
        "jd_keyword_frequency": freq
    }


def detect_action_verbs(text):
    text_lower = text.lower()
    found = [verb for verb in ACTION_VERBS if re.search(r'\b' + re.escape(verb) + r'\b', text_lower)]
    return sorted(found)


def detect_weak_phrases(text):
    text_lower = text.lower()
    found = [phrase for phrase in WEAK_PHRASES if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower)]
    return sorted(found)


def generate_suggestions(text, best_role, section_status, missing_skills, jd_missing_keywords):
    suggestions = []

    if not section_status.get("summary"):
        suggestions.append("Add a short professional summary at the top of your resume.")
    if not section_status.get("projects"):
        suggestions.append("Add a projects section to showcase practical work and problem-solving ability.")
    if not section_status.get("linkedin"):
        suggestions.append("Add your LinkedIn profile to improve professional visibility.")
    if not section_status.get("github"):
        suggestions.append("Add your GitHub profile, especially for technical roles.")
    if not section_status.get("certifications"):
        suggestions.append("Add certifications if you have completed relevant courses or training.")

    if missing_skills:
        suggestions.append(
            f"For the role '{best_role}', try adding or learning these important skills: {', '.join(missing_skills[:8])}."
        )

    if jd_missing_keywords:
        suggestions.append(
            f"Your resume is missing important job description keywords such as: {', '.join(jd_missing_keywords[:8])}."
        )

    weak_phrases_found = detect_weak_phrases(text)
    if weak_phrases_found:
        suggestions.append(
            "Replace weak phrases like 'worked on' or 'responsible for' with stronger action verbs such as developed, built, designed, or implemented."
        )

    action_verbs_found = detect_action_verbs(text)
    if not action_verbs_found:
        suggestions.append("Use stronger action verbs in project and experience bullet points.")

    if len(text.split()) < 150:
        suggestions.append("Your resume content looks short. Add more details, achievements, projects, and impact.")
    if len(text.split()) > 1200:
        suggestions.append("Your resume looks too long. Try keeping it concise and focused, ideally 1–2 pages.")

    if not re.search(r"\d+%|\d+\s*\+|\d+\s*users|\d+\s*projects|\d+\s*clients", text.lower()):
        suggestions.append("Add measurable achievements such as percentages, counts, or outcomes to strengthen your resume.")

    return suggestions[:8]


def calculate_ats_score(role_match, section_percent, jd_match_score, detected_skill_count):
    role_component = min(role_match, 40)
    section_component = round((section_percent / 100) * 25, 1)
    jd_component = round((jd_match_score / 100) * 20, 1)
    skill_component = min(detected_skill_count * 1.5, 15)

    total = round(role_component + section_component + jd_component + skill_component, 1)
    return min(total, 100)


def extract_basic_info(text):
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone_match = re.search(r"\+?\d[\d\s\-]{8,}\d", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    name_guess = None

    invalid_name_words = {
        "linkedin", "github", "http", "https", "www", "com", "in",
        "resume", "profile", "developer", "engineer", "analyst",
        "summary", "objective", "email", "phone", "mobile", "address"
    }

    # 1) Try to find a short clean line near the top
    for line in lines[:10]:
        test_line = line

        # remove urls
        test_line = re.sub(r"https?://\S+", "", test_line, flags=re.IGNORECASE)
        test_line = re.sub(r"www\.\S+", "", test_line, flags=re.IGNORECASE)

        # remove email and phone if present
        if email_match:
            test_line = test_line.replace(email_match.group(0), "")
        if phone_match:
            test_line = test_line.replace(phone_match.group(0), "")

        # keep only letters and spaces
        test_line = re.sub(r"[^A-Za-z\s]", " ", test_line)
        test_line = re.sub(r"\s+", " ", test_line).strip()

        if not test_line:
            continue

        words = test_line.split()

        # reject lines with obvious non-name words
        lower_words = [w.lower() for w in words]
        if any(word in invalid_name_words for word in lower_words):
            # but keep checking fallback from same line after cleaning
            cleaned_words = [w for w in words if w.lower() not in invalid_name_words]
            if 2 <= len(cleaned_words) <= 4:
                name_guess = " ".join(cleaned_words).title()
                break
            continue

        if 2 <= len(words) <= 4:
            name_guess = " ".join(words).title()
            break

    # 2) Fallback: use first few lines and extract probable name words
    if not name_guess:
        for line in lines[:5]:
            test_line = line

            test_line = re.sub(r"https?://\S+", "", test_line, flags=re.IGNORECASE)
            test_line = re.sub(r"www\.\S+", "", test_line, flags=re.IGNORECASE)

            if email_match:
                test_line = test_line.replace(email_match.group(0), "")
            if phone_match:
                test_line = test_line.replace(phone_match.group(0), "")

            test_line = re.sub(r"[^A-Za-z\s]", " ", test_line)
            test_line = re.sub(r"\s+", " ", test_line).strip()

            if not test_line:
                continue

            words = [w for w in test_line.split() if w.lower() not in invalid_name_words]

            # take first 2 to 3 clean words
            if len(words) >= 2:
                name_guess = " ".join(words[:3]).title()
                break

    if not name_guess:
        name_guess = "Not found"

    return {
        "name": name_guess,
        "email": email_match.group(0) if email_match else "Not found",
        "phone": phone_match.group(0) if phone_match else "Not found"
    }

def generate_interview_questions(detected_skills, target_role):
    questions = []

    for skill in detected_skills:
        skill_lower = skill.lower()
        if skill_lower in INTERVIEW_QUESTION_BANK:
            questions.extend(INTERVIEW_QUESTION_BANK[skill_lower])

    if target_role == "Software Developer":
        questions.extend([
            "Explain object-oriented programming and its core principles.",
            "How do you debug a production issue in a software application?"
        ])
    elif target_role == "Frontend Developer":
        questions.extend([
            "How do you optimize the performance of a frontend application?",
            "What are common accessibility improvements for web interfaces?"
        ])
    elif target_role == "Backend Developer":
        questions.extend([
            "How do you design a scalable backend service?",
            "What is database indexing and why is it useful?"
        ])
    elif target_role == "Data Analyst":
        questions.extend([
            "How do you clean messy real-world datasets before analysis?",
            "How would you explain a dashboard insight to a non-technical stakeholder?"
        ])
    elif target_role == "Machine Learning Engineer":
        questions.extend([
            "What steps are involved in deploying a machine learning model to production?",
            "How do you monitor model drift after deployment?"
        ])

    unique_questions = []
    seen = set()
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique_questions.append(q)

    return unique_questions[:10]


def generate_cover_letter(name, target_role, detected_skills, job_description):
    skill_text = ", ".join(detected_skills[:6]) if detected_skills else "relevant technical skills"
    jd_line = "I am especially interested in this opportunity because it closely matches my background and career goals." \
        if job_description.strip() else \
        "I am excited to apply my skills and projects to a role that aligns with my interests."

    return (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to express my interest in the {target_role} position. "
        f"My background includes experience with {skill_text}, and I have developed practical skills through projects, coursework, and hands-on learning.\n\n"
        f"{jd_line} I am motivated to contribute, learn quickly, and grow in a collaborative environment. "
        f"I believe my foundation and enthusiasm make me a strong candidate for this role.\n\n"
        f"Thank you for your time and consideration. I would welcome the opportunity to discuss my profile further.\n\n"
        f"Sincerely,\n{name}"
    )


def generate_learning_roadmap(target_role, missing_skills):
    roadmap = []
    if not missing_skills:
        return [
            f"You already match many skills for {target_role}.",
            "Build advanced portfolio projects in this role.",
            "Practice interview questions and system/problem-solving rounds.",
            "Apply to internships and entry-level openings."
        ]

    roadmap.append(f"Start with the most important missing skills for {target_role}.")
    for skill in missing_skills[:5]:
        roadmap.append(f"Learn and practice: {skill}")
    roadmap.append("Build one project that includes at least 2–3 of the missing skills.")
    roadmap.append("Update your resume after completing the project and re-run the analysis.")
    return roadmap[:8]


def categorize_skills(detected_skills):
    categories = {
        "Programming Languages": [],
        "Frameworks/Libraries": [],
        "Databases": [],
        "Cloud/DevOps": [],
        "Tools/Concepts": []
    }

    language_keywords = {"python", "java", "javascript", "typescript", "c++", "c#", "r", "php", "bash"}
    framework_keywords = {
        "react", "vue", "angular", "tensorflow", "keras", "pytorch",
        "flask", "django", "spring", "express", "scikit-learn", "jquery", "next.js"
    }
    database_keywords = {"sql", "mysql", "postgresql", "mongodb", "oracle", "sql server", "redis", "cassandra"}
    cloud_keywords = {"aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible", "jenkins", "ci/cd"}
    
    for skill in detected_skills:
        skill_lower = skill.lower()
        if skill_lower in language_keywords:
            categories["Programming Languages"].append(skill)
        elif skill_lower in framework_keywords:
            categories["Frameworks/Libraries"].append(skill)
        elif skill_lower in database_keywords:
            categories["Databases"].append(skill)
        elif skill_lower in cloud_keywords:
            categories["Cloud/DevOps"].append(skill)
        else:
            categories["Tools/Concepts"].append(skill)

    return categories


def detect_experience_level(text):
    text_lower = text.lower()
    year_matches = re.findall(r'(\d+)\+?\s+years?', text_lower)

    if "internship" in text_lower or "fresher" in text_lower:
        return "Fresher / Entry-Level"

    if year_matches:
        max_year = max(int(y) for y in year_matches)
        if max_year <= 1:
            return "Entry-Level"
        if max_year <= 3:
            return "Junior / Early Career"
        if max_year <= 6:
            return "Mid-Level"
        return "Senior"

    return "Fresher / Entry-Level"


def save_analysis_to_db(result):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO analysis_history (
            filename, best_role, ats_score, target_role, target_role_score,
            jd_match_score, created_at, result_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["filename"],
        result["best_role"],
        result["ats_score"],
        result["target_role"],
        result["target_role_score"],
        result["jd_match_score"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        json.dumps(result)
    ))
    conn.commit()
    conn.close()


def get_analysis_history():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, best_role, ats_score, target_role, target_role_score,
               jd_match_score, created_at
        FROM analysis_history
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_analysis_by_id(record_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT result_json FROM analysis_history WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', roles=JOB_ROLES.keys())


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    target_role = request.form.get('target_role', '').strip()
    job_description = request.form.get('job_description', '').strip()
    manual_name = request.form.get('manual_name', '').strip()
    manual_email = request.form.get('manual_email', '').strip()

    filename = file.filename.lower()
    text = ""

    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(file)
    else:
        return jsonify({'error': 'Only PDF and DOCX files are supported'}), 400

    if not text.strip():
        return jsonify({'error': 'Could not extract text from the file. Please ensure it is not scanned or image-based.'}), 400

    text = normalize_text(text)
    basic_info = extract_basic_info(text)
    if manual_name:
      basic_info["name"] = manual_name
    if manual_email:
      basic_info["email"] = manual_email
    detected_skills = extract_skills(text)
    categorized_skills = categorize_skills(detected_skills)
    experience_level = detect_experience_level(text)

    section_status = check_resume_sections(text)
    present_sections, total_sections, section_percent = section_score(section_status)

    role_matches = {role: calculate_match(detected_skills, skills) for role, skills in JOB_ROLES.items()}
    sorted_roles = dict(sorted(role_matches.items(), key=lambda x: x[1], reverse=True))
    best_role = max(role_matches, key=role_matches.get)
    best_score = role_matches[best_role]

    final_target_role = target_role if target_role in JOB_ROLES else best_role
    missing_skills = get_missing_skills(detected_skills, JOB_ROLES[final_target_role])

    job_desc_analysis = analyze_job_description(job_description, detected_skills)
    jd_match_score = job_desc_analysis["jd_match_score"]
    jd_missing_keywords = job_desc_analysis["jd_missing_keywords"]

    ats_score = calculate_ats_score(
        role_match=role_matches[final_target_role],
        section_percent=section_percent,
        jd_match_score=jd_match_score,
        detected_skill_count=len(detected_skills)
    )

    top_keywords = keyword_frequency(text, JOB_ROLES[final_target_role])

    suggestions = generate_suggestions(
        text=text,
        best_role=final_target_role,
        section_status=section_status,
        missing_skills=missing_skills,
        jd_missing_keywords=jd_missing_keywords
    )

    interview_questions = generate_interview_questions(detected_skills, final_target_role)
    cover_letter = generate_cover_letter(
        name=basic_info["name"],
        target_role=final_target_role,
        detected_skills=detected_skills,
        job_description=job_description
    )
    learning_roadmap = generate_learning_roadmap(final_target_role, missing_skills)

    result = {
        "filename": file.filename,
        "basic_info": basic_info,
        "experience_level": experience_level,
        "detected_skills": detected_skills,
        "categorized_skills": categorized_skills,
        "detected_skill_count": len(detected_skills),
        "role_matches": sorted_roles,
        "best_role": best_role,
        "best_score": best_score,
        "target_role": final_target_role,
        "target_role_score": role_matches[final_target_role],
        "missing_skills": missing_skills,
        "section_status": section_status,
        "present_sections": present_sections,
        "total_sections": total_sections,
        "section_percent": section_percent,
        "job_description": job_description,
        "jd_match_score": jd_match_score,
        "jd_detected_keywords": job_desc_analysis["jd_detected_keywords"],
        "jd_missing_keywords": jd_missing_keywords,
        "jd_keyword_frequency": job_desc_analysis["jd_keyword_frequency"],
        "ats_score": ats_score,
        "top_keywords": top_keywords,
        "suggestions": suggestions,
        "interview_questions": interview_questions,
        "cover_letter": cover_letter,
        "learning_roadmap": learning_roadmap
    }

    session['result'] = result
    save_analysis_to_db(result)

    return jsonify({'success': True, 'redirect': '/result'})


@app.route('/result')
def result():
    result = session.get('result')
    if not result:
        return render_template('index.html', roles=JOB_ROLES.keys())
    return render_template('result.html', result=result)


@app.route('/history')
def history():
    records = get_analysis_history()
    return render_template('history.html', records=records)


@app.route('/history/<int:record_id>')
def view_history_record(record_id):
    result = get_analysis_by_id(record_id)
    if not result:
        return redirect(url_for('history'))
    session['result'] = result
    return redirect(url_for('result'))


@app.route('/download-report')
def download_report():
    result = session.get('result')
    if not result:
        return "No report found", 404

    json_data = json.dumps(result, indent=4)
    buffer = io.BytesIO()
    buffer.write(json_data.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='resume_analysis_report.json',
        mimetype='application/json'
    )


@app.route('/download-pdf-report')
def download_pdf_report():
    result = session.get('result')
    if not result:
        return "No report found", 404

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        x = 40
        y = height - 50

        def write_line(text, font="Helvetica", size=10, gap=16):
            nonlocal y
            if y < 60:
                pdf.showPage()
                y = height - 50
            pdf.setFont(font, size)
            pdf.drawString(x, y, text[:110])
            y -= gap

        pdf.setTitle("Resume Analysis Report")

        write_line("AI Resume Analyzer Report", "Helvetica-Bold", 16, 24)
        write_line(f"Filename: {result['filename']}", size=11)
        write_line(f"Candidate: {result['basic_info']['name']}", size=11)
        write_line(f"Email: {result['basic_info']['email']}", size=11)
        write_line(f"Phone: {result['basic_info']['phone']}", size=11)
        write_line(f"Experience Level: {result['experience_level']}", size=11)
        write_line(f"ATS Score: {result['ats_score']}%", "Helvetica-Bold", 12, 18)
        write_line(f"Best Role: {result['best_role']}", size=11)
        write_line(f"Target Role: {result['target_role']}", size=11)
        write_line(f"Target Role Match: {result['target_role_score']}%", size=11)
        write_line(f"JD Match: {result['jd_match_score']}%", size=11, gap=20)

        write_line("Detected Skills:", "Helvetica-Bold", 12, 18)
        for skill in result["detected_skills"][:20]:
            write_line(f"- {skill}")

        write_line("Missing Skills:", "Helvetica-Bold", 12, 18)
        for skill in result["missing_skills"][:15]:
            write_line(f"- {skill}")

        write_line("Suggestions:", "Helvetica-Bold", 12, 18)
        for suggestion in result["suggestions"][:8]:
            write_line(f"- {suggestion[:100]}")

        write_line("Interview Questions:", "Helvetica-Bold", 12, 18)
        for q in result["interview_questions"][:8]:
            write_line(f"- {q[:100]}")

        pdf.save()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="resume_analysis_report.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return f"PDF generation error: {str(e)}", 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'logo-192.png',
        mimetype='image/png'
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)