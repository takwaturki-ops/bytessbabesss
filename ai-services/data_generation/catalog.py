"""SIMULATED 9antra course catalog.

Every course, price and description here is fictional and generated for a hackathon
prototype. None of it describes a real 9antra offer.
"""

COURSES: list[dict] = [
    {
        "course_id": "C001", "title": "AI Foundations for Everyone", "title_ar": "أساسيات الذكاء الاصطناعي للجميع",
        "category": "foundations", "level": "beginner", "price_tnd": 149.0, "duration_hours": 12, "duration_weeks": 3,
        "prerequisites": [], "language": "ar/fr", "format": "self-paced", "certificate": True,
        "keywords": ["ai", "basics", "beginner", "introduction", "ذكاء", "debutant", "intro"],
        "description": "Non-technical introduction to AI concepts, use cases and limits.",
    },
    {
        "course_id": "C002", "title": "Python for AI", "title_ar": "بايثون للذكاء الاصطناعي",
        "category": "programming", "level": "beginner", "price_tnd": 199.0, "duration_hours": 20, "duration_weeks": 4,
        "prerequisites": [], "language": "fr", "format": "self-paced", "certificate": True,
        "keywords": ["python", "programming", "code", "coding", "بايثون", "programmation"],
        "description": "Python basics, NumPy and pandas, aimed at future AI practitioners.",
    },
    {
        "course_id": "C003", "title": "Machine Learning Essentials", "title_ar": "أساسيات تعلم الآلة",
        "category": "machine_learning", "level": "intermediate", "price_tnd": 349.0, "duration_hours": 32, "duration_weeks": 6,
        "prerequisites": ["C002"], "language": "fr", "format": "live+self-paced", "certificate": True,
        "keywords": ["machine learning", "ml", "scikit", "regression", "classification", "تعلم الآلة"],
        "description": "Supervised and unsupervised learning with scikit-learn on real-style datasets.",
    },
    {
        "course_id": "C004", "title": "Deep Learning with PyTorch", "title_ar": "التعلم العميق باستخدام PyTorch",
        "category": "machine_learning", "level": "advanced", "price_tnd": 499.0, "duration_hours": 40, "duration_weeks": 8,
        "prerequisites": ["C003"], "language": "fr/en", "format": "live", "certificate": True,
        "keywords": ["deep learning", "pytorch", "neural", "cnn", "réseaux de neurones", "التعلم العميق"],
        "description": "Neural networks, CNNs and training best practices in PyTorch.",
    },
    {
        "course_id": "C005", "title": "Generative AI & Prompt Engineering", "title_ar": "الذكاء الاصطناعي التوليدي وهندسة الأوامر",
        "category": "generative_ai", "level": "beginner", "price_tnd": 179.0, "duration_hours": 10, "duration_weeks": 2,
        "prerequisites": [], "language": "ar/fr", "format": "self-paced", "certificate": True,
        "keywords": ["prompt", "chatgpt", "generative", "llm", "genai", "توليدي", "chatbot"],
        "description": "Practical prompting and everyday productivity with generative AI tools.",
    },
    {
        "course_id": "C006", "title": "Building LLM Applications", "title_ar": "بناء تطبيقات النماذج اللغوية",
        "category": "generative_ai", "level": "advanced", "price_tnd": 549.0, "duration_hours": 36, "duration_weeks": 6,
        "prerequisites": ["C002", "C005"], "language": "en/fr", "format": "live", "certificate": True,
        "keywords": ["rag", "agents", "llm apps", "api", "langchain", "vector", "application"],
        "description": "RAG, tool use and AI agents: build and deploy LLM-powered apps.",
    },
    {
        "course_id": "C007", "title": "Data Analysis with AI", "title_ar": "تحليل البيانات بالذكاء الاصطناعي",
        "category": "data", "level": "beginner", "price_tnd": 229.0, "duration_hours": 18, "duration_weeks": 4,
        "prerequisites": [], "language": "fr", "format": "self-paced", "certificate": True,
        "keywords": ["data", "excel", "analysis", "dashboard", "analyse", "تحليل البيانات", "power bi"],
        "description": "Analyse business data with spreadsheets, Python and AI assistants.",
    },
    {
        "course_id": "C008", "title": "AI for Marketing & Sales", "title_ar": "الذكاء الاصطناعي للتسويق والمبيعات",
        "category": "business", "level": "beginner", "price_tnd": 199.0, "duration_hours": 12, "duration_weeks": 3,
        "prerequisites": [], "language": "ar/fr", "format": "self-paced", "certificate": True,
        "keywords": ["marketing", "sales", "social media", "content", "تسويق", "ventes", "ads"],
        "description": "Use AI for content creation, campaign optimisation and lead scoring.",
    },
    {
        "course_id": "C009", "title": "AI in FinTech", "title_ar": "الذكاء الاصطناعي في التكنولوجيا المالية",
        "category": "business", "level": "intermediate", "price_tnd": 399.0, "duration_hours": 24, "duration_weeks": 5,
        "prerequisites": ["C001"], "language": "fr/en", "format": "live+self-paced", "certificate": True,
        "keywords": ["fintech", "finance", "fraud", "banking", "credit", "مالية", "bank"],
        "description": "Credit scoring, fraud detection and compliance use cases in finance.",
    },
    {
        "course_id": "C010", "title": "Computer Vision Bootcamp", "title_ar": "معسكر الرؤية الحاسوبية",
        "category": "machine_learning", "level": "advanced", "price_tnd": 599.0, "duration_hours": 48, "duration_weeks": 8,
        "prerequisites": ["C003"], "language": "fr/en", "format": "live", "certificate": True,
        "keywords": ["vision", "image", "opencv", "yolo", "detection", "رؤية حاسوبية"],
        "description": "Image classification, object detection and deployment of vision models.",
    },
    {
        "course_id": "C011", "title": "AI Strategy for Managers", "title_ar": "استراتيجية الذكاء الاصطناعي للمديرين",
        "category": "business", "level": "intermediate", "price_tnd": 449.0, "duration_hours": 14, "duration_weeks": 2,
        "prerequisites": [], "language": "fr/en", "format": "live", "certificate": True,
        "keywords": ["strategy", "manager", "leadership", "roi", "transformation", "entreprise", "استراتيجية"],
        "description": "Plan AI adoption, evaluate ROI and manage AI projects in a company.",
    },
    {
        "course_id": "C012", "title": "MLOps & Model Deployment", "title_ar": "عمليات تعلم الآلة ونشر النماذج",
        "category": "engineering", "level": "advanced", "price_tnd": 529.0, "duration_hours": 30, "duration_weeks": 5,
        "prerequisites": ["C003"], "language": "en/fr", "format": "live", "certificate": True,
        "keywords": ["mlops", "deployment", "docker", "monitoring", "production", "devops", "نشر"],
        "description": "Package, deploy and monitor ML models with Docker, CI/CD and monitoring.",
    },
]

DISCOUNT_CODES: dict[str, float] = {"WELCOME10": 0.10, "STUDENT20": 0.20, "HACK15": 0.15}
