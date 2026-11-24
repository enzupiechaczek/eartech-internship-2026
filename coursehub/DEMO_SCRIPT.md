# CourseHub — Final Demo Script

**Estimated Duration:** 5–7 minutes  
**Flow:** `Register → Create → Enroll → Learn → Review`

---

## 1. Pre-Demo Setup

Run the following commands inside the `coursehub/` directory before starting the presentation:

```bash
python manage.py migrate
python manage.py seed_data --clear
python manage.py runserver