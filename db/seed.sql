-- SIMULATED course catalog, identical to the AI service catalog (ai-services/data_generation/catalog.py).
-- Safe to re-run: existing rows are left untouched.
INSERT INTO courses (id, title, title_ar, category, level, price_tnd, duration_hours, duration_weeks, description) VALUES
('C001', 'AI Foundations for Everyone', 'أساسيات الذكاء الاصطناعي للجميع', 'foundations', 'beginner', 149.00, 12, 3, 'Non-technical introduction to AI concepts, use cases and limits.'),
('C002', 'Python for AI', 'بايثون للذكاء الاصطناعي', 'programming', 'beginner', 199.00, 20, 4, 'Python basics, NumPy and pandas, aimed at future AI practitioners.'),
('C003', 'Machine Learning Essentials', 'أساسيات تعلم الآلة', 'machine_learning', 'intermediate', 349.00, 32, 6, 'Supervised and unsupervised learning with scikit-learn on real-style datasets.'),
('C004', 'Deep Learning with PyTorch', 'التعلم العميق باستخدام PyTorch', 'machine_learning', 'advanced', 499.00, 40, 8, 'Neural networks, CNNs and training best practices in PyTorch.'),
('C005', 'Generative AI & Prompt Engineering', 'الذكاء الاصطناعي التوليدي وهندسة الأوامر', 'generative_ai', 'beginner', 179.00, 10, 2, 'Practical prompting and everyday productivity with generative AI tools.'),
('C006', 'Building LLM Applications', 'بناء تطبيقات النماذج اللغوية', 'generative_ai', 'advanced', 549.00, 36, 6, 'RAG, tool use and AI agents: build and deploy LLM-powered apps.'),
('C007', 'Data Analysis with AI', 'تحليل البيانات بالذكاء الاصطناعي', 'data', 'beginner', 229.00, 18, 4, 'Analyse business data with spreadsheets, Python and AI assistants.'),
('C008', 'AI for Marketing & Sales', 'الذكاء الاصطناعي للتسويق والمبيعات', 'business', 'beginner', 199.00, 12, 3, 'Use AI for content creation, campaign optimisation and lead scoring.'),
('C009', 'AI in FinTech', 'الذكاء الاصطناعي في التكنولوجيا المالية', 'business', 'intermediate', 399.00, 24, 5, 'Credit scoring, fraud detection and compliance use cases in finance.'),
('C010', 'Computer Vision Bootcamp', 'معسكر الرؤية الحاسوبية', 'machine_learning', 'advanced', 599.00, 48, 8, 'Image classification, object detection and deployment of vision models.'),
('C011', 'AI Strategy for Managers', 'استراتيجية الذكاء الاصطناعي للمديرين', 'business', 'intermediate', 449.00, 14, 2, 'Plan AI adoption, evaluate ROI and manage AI projects in a company.'),
('C012', 'MLOps & Model Deployment', 'عمليات تعلم الآلة ونشر النماذج', 'engineering', 'advanced', 529.00, 30, 5, 'Package, deploy and monitor ML models with Docker, CI/CD and monitoring.')
ON CONFLICT (id) DO NOTHING;
