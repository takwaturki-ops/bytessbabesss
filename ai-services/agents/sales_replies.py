"""Localized, structured replies for the Sales Agent (mock mode and guardrail fallback).

Every fact (title, price, duration, level, prerequisites, certificate) comes from the catalog; only the wording
is templated. Replies use a light markup the frontend renders: blank-line paragraphs, "• " bullets, **bold**.
Wording varies with the message (stable hash), so the same question always gets the same answer (testable)
while different questions do not all read alike.
"""
from __future__ import annotations

import zlib

from core import data

LANGS = ("fr", "tn", "en")

LEVEL = {
    "fr": {"beginner": "débutant", "intermediate": "intermédiaire", "advanced": "avancé"},
    "tn": {"beginner": "débutant", "intermediate": "intermédiaire", "advanced": "avancé"},
    "en": {"beginner": "beginner", "intermediate": "intermediate", "advanced": "advanced"},
}
FORMAT = {
    "fr": {"self-paced": "à ton rythme", "live": "en live", "live+self-paced": "live + à ton rythme"},
    "tn": {"self-paced": "3la rou7ek", "live": "en live", "live+self-paced": "live + 3la rou7ek"},
    "en": {"self-paced": "self-paced", "live": "live", "live+self-paced": "live + self-paced"},
}
WEEKS = {"fr": "semaines", "tn": "jem3at", "en": "weeks"}

DESC_FR = {
    "C001": "Une introduction non technique : concepts, usages et limites de l'IA.",
    "C002": "Les bases de Python, NumPy et pandas pour se lancer dans l'IA.",
    "C003": "L'apprentissage supervisé et non supervisé avec scikit-learn, sur des cas concrets.",
    "C004": "Réseaux de neurones, CNN et bonnes pratiques d'entraînement avec PyTorch.",
    "C005": "Le prompting en pratique et la productivité au quotidien avec l'IA générative.",
    "C006": "RAG, outils et agents IA : construire et déployer des applications LLM.",
    "C007": "Analyser des données business avec tableurs, Python et assistants IA.",
    "C008": "L'IA pour créer du contenu, optimiser les campagnes et scorer les prospects.",
    "C009": "Scoring de crédit, détection de fraude et conformité dans la finance.",
    "C010": "Classification d'images, détection d'objets et déploiement de modèles de vision.",
    "C011": "Planifier l'adoption de l'IA, évaluer le ROI et piloter des projets IA.",
    "C012": "Packager, déployer et monitorer des modèles ML (Docker, CI/CD, monitoring).",
}

REASON = {
    "fr": {"requested": "le cours que tu as choisi", "match": "correspond à ta demande",
           "starter": "idéal pour débuter", "cheaper": "option plus abordable", "goal": "colle à ton objectif",
           "short": "le plus court", "beginner": "sans prérequis, pour débutants", "compared": "cours comparé",
           "popular": "très demandé"},
    "tn": {"requested": "el cours elli khtartou", "match": "yemchi m3a talbek", "starter": "behi bech tebda",
           "cheaper": "arkhes", "goal": "yemchi m3a hadfek", "short": "a9sar cours",
           "beginner": "lel débutants, bla prérequis", "compared": "cours comparé", "popular": "barcha ytalbouh"},
    "en": {"requested": "the course you asked for", "match": "best match for your request",
           "starter": "great place to start", "cheaper": "more affordable option", "goal": "matches your goal",
           "short": "shortest relevant course", "beginner": "beginner-friendly, no prerequisites",
           "compared": "compared course", "popular": "popular pick"},
}

# Each entry is a list of variants; one is picked per message.
T: dict[str, dict[str, list[str]]] = {
    "fr": {
        "hello": ["Ahla bik ! 👋 Moi c'est l'assistant de 9antra.", "Coucou ! 😊 Bienvenue sur 9antra.",
                  "Salut ! 👋 Ravi de te voir sur 9antra."],
        "hello_again": ["Re ! 😊", "Content de te revoir !", "Toujours là pour toi !"],
        "offer_help": ["Je t'aide à trouver la formation IA qui te correspond : ton niveau, ton budget, ton temps."],
        "ask_goal": ["Dis-moi ce qui t'intéresse, par exemple :\n• l'**IA générative** et le prompting\n"
                     "• **Python** et la data\n• le **machine learning**\n• l'**IA pour ton métier** (marketing, finance, management)",
                     "Tu veux apprendre quoi ? Quelques pistes :\n• **débuter** en IA sans coder\n"
                     "• **programmer** avec Python\n• aller vers le **machine learning**\n• utiliser l'IA **au travail**"],
        "whoami": ["Je suis l'assistant commercial de 9antra 🤖. Je peux :\n• te **recommander** un cours selon ton objectif\n"
                   "• **comparer** deux formations\n• trouver une option **moins chère** ou **plus courte**\n"
                   "• lancer ton **inscription**"],
        "thanks": ["Avec plaisir ! 😊", "De rien, c'est mon job ! 🙌", "Je t'en prie !"],
        "thanks_more": ["Autre chose ? Je peux comparer des cours ou t'aider à t'inscrire.",
                        "Si tu as une autre question, je suis là."],
        "farewell": ["À bientôt sur 9antra ! 👋 Bonne continuation.", "Bslema ! Reviens quand tu veux. 😊"],
        "catalog": ["Voici un aperçu de notre catalogue ({n} formations), du plus accessible au plus avancé :",
                    "On a {n} formations en IA. Pour démarrer, voici les plus populaires :"],
        "present": ["Voici ce que je te propose :", "J'ai trouvé ce qui te correspond :",
                    "Bonne idée ! Voilà mes recommandations :"],
        "prereq": ["ℹ️ **{title}** demande d'avoir suivi : {prereqs}."],
        "close_present": ["👉 Tu veux plus de détails, une comparaison, ou tu te lances ?",
                          "👉 Lequel te tente le plus ? Je peux aussi les comparer pour toi.",
                          "👉 Dis-moi ton niveau et ton budget, et j'affine la sélection."],
        "purchase": ["Excellent choix ! ✅", "Super décision ! 🚀", "Parfait, on y va ! ✅"],
        "purchase_next": ["Clique sur **Acheter** juste en dessous pour lancer le paiement sécurisé (simulé). "
                          "Rien n'est débité sans ta confirmation."],
        "compare": ["Voici la comparaison :", "Comparons-les point par point :"],
        "advice_path": ["💡 Mon conseil : commence par **{a}**, puis enchaîne avec **{b}**."],
        "advice_cheap": ["💡 Mon conseil : **{a}** pour un premier pas plus abordable, **{b}** si tu veux un programme plus complet."],
        "price_ack": ["Je comprends, le budget compte. 💸", "Pas de souci, on trouve une solution adaptée à ton budget."],
        "price_cheaper": ["Une alternative plus légère :"],
        "price_student": ["🎓 Étudiant ? Avec le code **STUDENT20** (-20 %), {title} passe à **{price:.2f} TND**."],
        "price_none": ["C'est déjà l'option la plus accessible de cette thématique."],
        "time_ack": ["Je comprends, ton temps est précieux. ⏱️", "Pas de panique si tu es occupé·e !"],
        "time_detail": ["Compte environ **{hpw} h par semaine** ({hours} h au total), {fmt}."],
        "diff_ack": ["Aucun souci, tout le monde commence quelque part ! 💪", "Pas besoin d'être expert pour démarrer. 💪"],
        "diff_ok": ["Ce cours est pensé pour les débutants, **sans prérequis**."],
        "diff_prereq": ["Ce cours demande d'avoir suivi : {prereqs}."],
        "trust": ["Bonne question ! Voici ce qui est inclus :"],
        "trust_cert": ["• 🎓 **certificat** de réussite inclus", "• 🎓 pas de certificat pour ce cours"],
        "trust_more": ["• format : {fmt}\n• durée : {weeks} {weeks_word} ({hours} h)\n• niveau : {level}"],
        "pay_issue": ["Désolé pour ce souci de paiement. 🙏\n\n• Je transmets ton dossier à l'équipe paiement.\n"
                      "• **Aucun nouveau débit** ne sera effectué.\n• Tu seras recontacté·e rapidement."],
        "support": ["Désolé pour ce problème ! 🙏\n\n• Notre équipe support prend le relais.\n"
                    "• En attendant, vérifie ton e-mail et essaie de te reconnecter.\n• On revient vers toi très vite."],
        "not_interested": ["Pas de problème, merci pour ton temps ! 😊 Si tu changes d'avis, je suis là."],
        "clarify": ["Je veux être sûr de bien te conseiller : quel est ton objectif ? Et ton niveau actuel ?"],
    },
    "tn": {
        "hello": ["Ahla w sahla ! 👋 Ena l'assistant mta3 9antra.", "3aslema ! 😊 Marhba bik fi 9antra.",
                  "Ahla bik ! 👋 Mar7ba bik fi 9antra."],
        "hello_again": ["Ahla mella ! 😊", "Marhba bik mel jdid !"],
        "offer_help": ["N3awnek tal9a el formation IA elli tensbek : 3la 7seb niveau mte3ek, budget w wa9tek."],
        "ask_goal": ["Chnowa t7eb tet3allem ? Par exemple :\n• l'**IA générative** w el prompting\n"
                     "• **Python** w el data\n• el **machine learning**\n• l'**IA fi khedmtek** (marketing, finance, management)"],
        "whoami": ["Ena l'assistant mta3 9antra 🤖. Najjem :\n• **nwassik** b cours 3la 7seb hadfek\n"
                   "• **n9aren** binet zouz formations\n• nal9alek option **arkhes** walla **a9sar**\n"
                   "• n3awnek **tetsajjel**"],
        "thanks": ["Bla jmil ! 😊", "3la rasi ! 🙌", "Ya3tik saha enti !"],
        "thanks_more": ["T7eb haja okhra ? Najjem n9aren cours walla n3awnek tetsajjel."],
        "farewell": ["Bslema ! 👋 Narj3ou nchoufouk 9rib fi 9antra.", "Bslema w rabbi y3awnek ! 😊"],
        "catalog": ["Hédha aperçu 3al catalogue mte3na ({n} formations) :",
                    "3andna {n} formations fi l'IA. Hédhom elli barcha ytalbouhom :"],
        "present": ["Hédha elli nwassik bih :", "L9itlek hédhom :", "Fekra behya ! Chouf hédhom :"],
        "prereq": ["ℹ️ **{title}** lazmou tkoun 9rit 9bal : {prereqs}."],
        "close_present": ["👉 T7eb tafasil okhra, comparaison, walla tebda tawa ?",
                          "👉 Ama wa7ed y3ejbek akther ? Najjem n9arenhom."],
        "purchase": ["Ikhtiyar behi ! ✅", "Yesser behi ! 🚀"],
        "purchase_next": ["Enzel 3la **Acheter** louta bech tebda el paiement sécurisé (simulé). "
                          "Ma yetna7a 7atta flous 9bal ma t2akked."],
        "compare": ["Hédhi el comparaison :", "Nchoufou el far9 :"],
        "advice_path": ["💡 Nasi7ti : ebda b **{a}**, ba3d kammel b **{b}**."],
        "advice_cheap": ["💡 Nasi7ti : **{a}** ken t7eb tebda b 9al flous, **{b}** ken t7eb programme akmal."],
        "price_ack": ["Fhemtek, el budget mohem. 💸", "Ma famma 7atta mochkla, nal9aw 7al 3la 9ad budget mte3ek."],
        "price_cheaper": ["Famma option arkhes :"],
        "price_student": ["🎓 Etudiant ? B code **STUDENT20** (-20 %), {title} yweli b **{price:.2f} TND**."],
        "price_none": ["Hédha deja arkhes cours fi el thème hédha."],
        "time_ack": ["Fhemtek, wa9tek ghali. ⏱️", "Ma t5afech ken t5addem barcha !"],
        "time_detail": ["Y7eb **{hpw} h fel jem3a** ({hours} h en tout), {fmt}."],
        "diff_ack": ["Ma t5afech, kol wa7ed bda men sfer ! 💪"],
        "diff_ok": ["El cours hédha lel débutants, **bla prérequis**."],
        "diff_prereq": ["El cours hédha lazmou : {prereqs}."],
        "trust": ["Sou2el behi ! Hédha chnowa fih :"],
        "trust_cert": ["• 🎓 **certificat** inclus", "• 🎓 ma fihech certificat"],
        "trust_more": ["• format : {fmt}\n• modda : {weeks} {weeks_word} ({hours} h)\n• niveau : {level}"],
        "pay_issue": ["Sorry 3al mochkla fel paiement. 🙏\n\n• Nba3eth dossier mte3ek l'équipe paiement.\n"
                      "• **Ma yetna7a 7atta débit jdid.**\n• Yetsalou bik 9rib."],
        "support": ["Sorry 3al mochkla ! 🙏\n\n• L'équipe support bech t3awnek.\n"
                    "• Thabbet fel email mte3ek w 3awed odkhel.\n• Nraj3oulek 9rib."],
        "not_interested": ["Ma famma mochkla, ya3tik saha 3la wa9tek ! 😊 Ken tbaddel rayek, ena houni."],
        "clarify": ["Bech nwassik s7i7 : chnowa hadfek ? W chnowa niveau mte3ek tawa ?"],
    },
    "en": {
        "hello": ["Hi there! 👋 I'm the 9antra assistant.", "Hello! 😊 Welcome to 9antra."],
        "hello_again": ["Welcome back! 😊", "Hi again!"],
        "offer_help": ["I'll help you find the AI course that fits your level, budget and schedule."],
        "ask_goal": ["What would you like to learn? For example:\n• **generative AI** and prompting\n"
                     "• **Python** and data\n• **machine learning**\n• **AI for your job** (marketing, finance, management)"],
        "whoami": ["I'm 9antra's sales assistant 🤖. I can:\n• **recommend** a course for your goal\n"
                   "• **compare** two courses\n• find a **cheaper** or **shorter** option\n• start your **enrolment**"],
        "thanks": ["You're welcome! 😊", "Happy to help! 🙌"],
        "thanks_more": ["Anything else? I can compare courses or help you enrol."],
        "farewell": ["See you soon on 9antra! 👋", "Goodbye, and good luck with your learning! 😊"],
        "catalog": ["Here's an overview of our catalog ({n} courses):", "We offer {n} AI courses. Popular picks to start:"],
        "present": ["Here's what I recommend:", "These look like a great fit:", "Good idea! My recommendations:"],
        "prereq": ["ℹ️ **{title}** requires: {prereqs}."],
        "close_present": ["👉 Want more details, a comparison, or ready to enrol?",
                          "👉 Which one appeals to you? I can compare them too."],
        "purchase": ["Excellent choice! ✅", "Great decision! 🚀"],
        "purchase_next": ["Click **Buy** below to start the secure (simulated) checkout. Nothing is charged until you confirm."],
        "compare": ["Here's how they compare:", "Side by side:"],
        "advice_path": ["💡 My advice: start with **{a}**, then move on to **{b}**."],
        "advice_cheap": ["💡 My advice: **{a}** for a more affordable first step, **{b}** for a more complete program."],
        "price_ack": ["I understand, budget matters. 💸"],
        "price_cheaper": ["A lighter alternative:"],
        "price_student": ["🎓 Student? With code **STUDENT20** (-20%), {title} drops to **{price:.2f} TND**."],
        "price_none": ["It's already the most affordable option in this topic."],
        "time_ack": ["I understand you're busy. ⏱️"],
        "time_detail": ["Plan for about **{hpw} h per week** ({hours} h total), {fmt}."],
        "diff_ack": ["No worries, everyone starts somewhere! 💪"],
        "diff_ok": ["It's designed for beginners, with **no prerequisites**."],
        "diff_prereq": ["It requires: {prereqs}."],
        "trust": ["Good question! Here's what's included:"],
        "trust_cert": ["• 🎓 **certificate** of completion included", "• 🎓 no certificate for this course"],
        "trust_more": ["• format: {fmt}\n• duration: {weeks} {weeks_word} ({hours} h)\n• level: {level}"],
        "pay_issue": ["Sorry about the payment issue. 🙏\n\n• I'm forwarding your case to our payment team.\n"
                      "• **No new charge** will be made.\n• They'll get back to you shortly."],
        "support": ["Sorry about that! 🙏\n\n• Our support team will help you access your course.\n"
                    "• Meanwhile, check your email and try logging in again.\n• We'll be in touch very soon."],
        "not_interested": ["No problem, thank you for your time! 😊 I'm here if you change your mind."],
        "clarify": ["To advise you well: what's your goal, and what's your current level?"],
    },
}


def seed_of(text: str) -> int:
    return zlib.crc32(" ".join(text.lower().split()).encode("utf-8"))


class Writer:
    """Picks wording for one reply: language + a per-message seed for stable variation."""

    def __init__(self, lang: str = "fr", seed: int = 0):
        self.lang = lang if lang in LANGS else "fr"
        self.seed = seed
        self._n = 0

    def say(self, key: str, **kw) -> str:
        options = T[self.lang][key]
        self._n += 1
        text = options[(self.seed + self._n) % len(options)]
        return text.format(**kw) if kw else text

    def nth(self, key: str, i: int) -> str:
        return T[self.lang][key][i]

    def reason(self, key: str) -> str:
        return REASON[self.lang][key]

    def desc(self, c: dict) -> str:
        return c["description"] if self.lang == "en" else DESC_FR.get(c["course_id"], c["description"])

    def facts(self, c: dict) -> str:
        return f"{c['price_tnd']:.0f} TND · {c['duration_weeks']} {WEEKS[self.lang]} · {LEVEL[self.lang][c['level']]}"

    def bullet(self, c: dict, with_desc: bool = True) -> str:
        line = f"• **{c['title']}** — {self.facts(c)}"
        return line + (f"\n  {self.desc(c)}" if with_desc else "")

    def prereqs(self, c: dict) -> str:
        cmap = data.course_map()
        return ", ".join(f"**{cmap[p]['title']}**" for p in c["prerequisites"] if p in cmap)

    def fmt(self, c: dict) -> str:
        return FORMAT[self.lang].get(c["format"], c["format"])

    def hours_per_week(self, c: dict) -> int:
        return max(1, round(c["duration_hours"] / max(1, c["duration_weeks"])))

    def compare_block(self, c: dict) -> str:
        lines = [f"**{c['title']}**", f"• {self.facts(c)}", f"• {self.fmt(c)} · ~{self.hours_per_week(c)} h/"
                 + {"fr": "semaine", "tn": "jem3a", "en": "week"}[self.lang], f"• {self.desc(c)}"]
        if c["prerequisites"]:
            lines.append("• " + {"fr": "prérequis : ", "tn": "prérequis : ", "en": "prerequisites: "}[self.lang]
                         + self.prereqs(c))
        return "\n".join(lines)


def join(*parts: str) -> str:
    """Paragraphs separated by a blank line; empty parts dropped."""
    return "\n\n".join(p for p in parts if p)
