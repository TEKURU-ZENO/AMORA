"""50 clearly fictional personas for DEMO MODE (AMORA_DEMO=1) and for tests.

Every name, company and handle here is invented, and every link points at example.com so a
persona can never be mistaken for, or link to, a real person's profile. With demo mode off the
app purges these on startup: the live pool is real people scraped through Apify only.
"""
from __future__ import annotations

import random
import re

from app.models import InstagramData, InstagramPost, LinkedInData, LinkedInExperience

FIRST = ["Aarav", "Meera", "Kabir", "Ananya", "Rohan", "Ishita", "Vikram", "Tara", "Neel", "Sana",
         "Arjun", "Diya", "Kiran", "Zoya", "Aditya", "Nisha", "Farhan", "Leela", "Siddharth", "Riya",
         "Omar", "Priya", "Arnav", "Maya", "Yash",
         # 26-50 (appended, so the first 25 stay exactly as they were)
         "Ira", "Dev", "Saanvi", "Kabeer", "Aisha", "Rehan", "Tanvi", "Vihaan", "Noor", "Aryan",
         "Mira", "Kunal", "Anika", "Zain", "Pooja", "Ritvik", "Esha", "Nikhil", "Sara", "Varun",
         "Lavanya", "Imran", "Shreya", "Karan", "Alina"]
LAST = ["Iyer", "Kapoor", "Menon", "Rao", "Shah", "Bose", "Pillai", "Nair", "Joshi", "Das",
        "Reddy", "Kulkarni", "Sen", "Mirza", "Varma", "Ghosh", "Qureshi", "Thomas", "Banerjee", "Chawla",
        "Siddiqui", "Krishnan", "Arora", "Fernandes", "Patil",
        "Bhatt", "Saxena", "Gupta", "Malhotra", "Sheikh", "Khanna", "Desai", "Agarwal", "Hussain", "Mehra",
        "Pandey", "Bajaj", "Chopra", "Ahmed", "Hegde", "Trivedi", "Kaur", "Mishra", "D'Souza", "Kamath",
        "Ramesh", "Ansari", "Venkatesh", "Sethi", "Kurien"]
CITIES = ["Chennai", "Bengaluru", "Mumbai", "Pune", "Hyderabad", "Delhi"]
ROLES = [("ML Engineer", "Fictive Labs", "Building LLM evaluation pipelines in Python"),
         ("Product Designer", "Imaginary Studio", "UX research and design systems in Figma"),
         ("Resident Doctor", "Make-Believe Hospital", "Internal medicine residency, public health outreach"),
         ("Founder", "Notreal.ai", "Building a startup in fintech, shipping weekly"),
         ("Research Scholar", "Institute of Pretend Science", "PhD research in neuroscience, two publications"),
         ("Data Scientist", "Placeholder Analytics", "Forecasting and data science for retail"),
         ("Architect", "Sample & Co", "Sustainable housing design and architecture"),
         ("Teacher", "Fable School", "Teaching kids maths, running a weekend library"),
         ("Investment Analyst", "Hypothetical Capital", "Venture investing in climate startups"),
         ("Software Engineer", "Mock Systems", "Backend software engineer, open source on weekends"),
         ("Chef", "Pretend Kitchen", "Running a small restaurant kitchen, seasonal menus"),
         ("Journalist", "The Imaginary Times", "Long-form reporting on cities and culture"),
         ("Musician", "Fictional Records", "Session guitarist and composer for indie films"),
         ("Lawyer", "Example & Partners", "Public interest law and policy research"),
         ("Game Developer", "Placeholder Games", "Building indie games in Unity and C#")]
POSTS = {
    "run": ["Sunday long run done, 21k by the river #running #halfmarathon", "New PB at the 10k #strava #run"],
    "hike": ["Summit at 6am, worth every step #trekking #himalaya", "Weekend trail with the crew #hiking"],
    "cook": ["Homemade sourdough attempt #4 #baking", "Sunday biryani for the whole family #cooking"],
    "photo": ["Golden hour on 35mm #photography #filmcamera", "Photo walk through old town #portrait"],
    "music": ["Open mic night, played two originals #guitar #gig", "Carnatic practice before work #violin"],
    "read": ["October reading stack #bookstagram #books", "Finished this novel in one sitting #reading"],
    "travel": ["Backpacking through the hills #travel #wanderlust", "Solo trip, no plans #roadtrip"],
    "game": ["Board game night, I lost again #chess #gaming", "Late night valorant with the squad #gaming"],
    "yoga": ["Beach yoga at sunrise #yoga #mindful", "10 days of vipassana, came back quieter #meditation"],
    "pets": ["This rescue pup runs my life #dog #rescue", "Cat refuses to let me work #cat"],
    "party": ["Rooftop birthday chaos #party #cocktails", "Friday nightout with the gang #club"],
    "volunteer": ["Volunteering at the shelter this weekend #volunteer #ngo", "Teaching kids coding on saturdays #impact"],
    "film": ["Letterboxd diary is getting out of hand #film #cinema", "Anime marathon weekend #anime"],
    "plants": ["Terrace garden finally blooming #plants #gardening", "Monstera update #plants"],
    "dance": ["Salsa social was so much fun #salsa #dance", "Bharatanatyam rehearsal #dance"],
    "climb": ["Finally sent my project at the gym #bouldering #climbing"],
    "food": ["Best filter coffee in the city #coffee #cafe", "Street food crawl #streetfood #foodie"],
    "family": ["Diwali with the whole family #family", "My niece is the boss now #family"],
}
PLACES = ["Marina Beach", "Kodaikanal", "Pondicherry", "Goa", "Rishikesh", "Hampi", "Munnar", "Ooty", ""]


def build() -> list[tuple[str, LinkedInData, InstagramData]]:
    r = random.Random(42)
    out = []
    keys = list(POSTS)
    for i in range(len(FIRST)):
        name = f"{FIRST[i]} {LAST[i]}"
        handle = re.sub(r"[^a-z0-9]+", "-", f"{FIRST[i]} {LAST[i]}".lower()) + "-test"  # D'Souza -> dsouza
        role = ROLES[i % len(ROLES)]
        prev = ROLES[(i + 3) % len(ROLES)]
        likes = r.sample(keys, k=r.randint(3, 5))
        posts = []
        for k in likes:
            for cap in POSTS[k]:
                posts.append(InstagramPost(caption=cap, hashtags=[t[1:] for t in cap.split() if t.startswith("#")],
                                           location=r.choice(PLACES)))
        r.shuffle(posts)
        ig_handle = handle.replace("-", "_")
        li = LinkedInData(
            url=f"https://example.com/linkedin/{handle}",
            full_name=name, headline=f"{role[0]} at {role[1]}", location=CITIES[i % len(CITIES)],
            about=f"{role[2]}. Outside work: {', '.join(likes[:2])}.",
            experience=[LinkedInExperience(title=role[0], company=role[1], duration="2024 - present", description=role[2]),
                        LinkedInExperience(title=prev[0], company=prev[1], duration="2022 - 2024", description=prev[2])],
            education=["Fictional University"], skills=role[2].split()[:4],
            volunteering=["Weekend teaching volunteer"] if "volunteer" in likes else [],
        )
        ig = InstagramData(url=f"https://example.com/instagram/{ig_handle}", username=ig_handle, full_name=name,
                           bio=f"{role[0].lower()} · {' · '.join(likes[:3])}", followers=r.randint(200, 3000),
                           following=r.randint(200, 900), posts=posts)
        out.append((handle, li, ig))
    return out
