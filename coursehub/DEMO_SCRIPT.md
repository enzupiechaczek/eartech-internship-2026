# CourseHub — Final Demo Script

**Estimated Duration:** 5–7 minutes  
**Flow:** `Register → Create → Enroll → Learn → Review`

---

## 1. Pre-Demo Setup

Run the following commands inside the `coursehub/` directory before starting the presentation:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data --clear
python manage.py runserver
```

Open `[http://127.0.0.1:8000/](http://127.0.0.1:8000/)` in your browser.

---

## 2. Demo Accounts

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin1234!` | Django Admin & full overview |
| **Instructor 1** | `instructor_sarah` | `Demo1234!` | Published & Draft courses in Creator Studio |
| **Instructor 2** | `instructor_omar` | `Demo1234!` | Cybersecurity course owner |
| **Student 1** | `student_alex` | `Demo1234!` | Active learner (50% Django, 100% Python + Review) |
| **Student 2** | `student_maya` | `Demo1234!` | Active learner (50% Security + Django Review) |

---

## 3. Live Presentation Walkthrough

### Step 1: Register (New Student Onboarding — ~1 min)
1. Show the landing page (`/`), including the **Most Popular Courses** section, and browse the catalogue (`/courses/`) with search and category filters.
2. Click **Register** (`/accounts/register/`), create a new student account (e.g., `demo_student`), and show automatic login.

### Step 2: Create (Instructor Studio & Curriculum — ~1.5 min)
1. Log out and sign in as **`instructor_sarah`** (`Demo1234!`).
2. Open **Creator Studio** (`/studio/`) to show published courses alongside **`Applied Machine Learning with Python (Draft)`**.
3. Click **+ Create New Course** (`/courses/new/`), create a sample course, add a module and a lesson using a valid video link (e.g., `[https://vimeo.com/76979871](https://vimeo.com/76979871)`), and toggle **Publish**.

### Step 3: Enroll (Student Discovery & Enrollment — ~1 min)
1. Log out and sign in as **`student_alex`** (`Demo1234!`).
2. Open **Practical Ethical Hacking & Web Security** from `/courses/` and click **Enroll**.
3. Navigate to **My Learning** (`/enrollments/my-learning/`) to confirm the course appears immediately.

### Step 4: Learn (Lesson Player & Progress Tracking — ~1 min)
1. Open **Full-Stack Web Development with Django** from **My Learning** (currently at **50%** progress).
2. Play the embedded lesson video, read the lesson notes, and mark a remaining lesson as **Completed** to watch the progress bar update dynamically.

### Step 5: Review (Course Rating & Feedback — ~1 min)
1. Open a completed course outline (e.g., **Python Programming Masterclass: Zero to Hero** at `/courses/2/outline/`).
2. Show existing student reviews and rating summary, and submit/update a course review to demonstrate live feedback validation.