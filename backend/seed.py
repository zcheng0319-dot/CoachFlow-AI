from pathlib import Path

from db import DB_PATH, get_connection


COACHES = [
    (1, "王晨", "男", "低龄启蒙与兴趣建立", "beginner"),
    (2, "李浩", "男", "正反手基础与动作纠正", "foundation"),
    (3, "张琪", "女", "零基础与女生兴趣培养", "beginner"),
    (4, "陈宇", "男", "步法与多球训练", "intermediate"),
    (5, "刘哲", "男", "发球与接发专项", "intermediate"),
    (6, "赵琳", "女", "6-9岁儿童启蒙", "beginner"),
    (7, "周凯", "男", "青少年体能与步法", "advanced"),
    (8, "孙悦", "女", "兴趣课程与初学者", "beginner"),
    (9, "吴昊", "男", "1v1技术纠正", "all_levels"),
    (10, "何佳", "女", "青少年比赛与战术", "advanced"),
]

COURSES = [
    (1, "少儿乒乓球启蒙班", 5, 7, "beginner", 1800, 16),
    (2, "少儿乒乓球基础班", 7, 10, "foundation", 2600, 20),
    (3, "少儿乒乓球进阶班", 8, 12, "intermediate", 3600, 24),
    (4, "青少年竞赛班", 10, 15, "advanced", 5200, 24),
    (5, "乒乓球1v1私教", 6, 15, "all_levels", 6000, 12),
    (6, "周末兴趣班", 6, 11, "beginner", 1600, 12),
]

CLASSES = [
    (1, 1, 1, "周一", "18:30", 8, 7),
    (2, 2, 2, "周二", "18:30", 10, 9),
    (3, 2, 3, "周三", "18:30", 10, 5),
    (4, 3, 4, "周四", "19:00", 8, 4),
    (5, 4, 10, "周五", "19:00", 10, 6),
    (6, 6, 6, "周六", "09:00", 12, 3),
    (7, 2, 8, "周六", "14:00", 10, 8),
    (8, 3, 5, "周六", "16:00", 8, 5),
    (9, 1, 1, "周日", "09:00", 8, 6),
    (10, 4, 7, "周日", "15:00", 10, 4),
]

LEADS = [
    (1, "张女士", "张子轩", 9, "beginner", "weekend", "trial_completed", "2026-08-20 10:00"),
    (2, "陈女士", "陈乐乐", 8, "foundation", "weekend", "trial_completed", "2026-08-18 11:00"),
    (3, "王先生", "王可", 7, "beginner", "weekday evening", "new", "2026-09-01 09:30"),
    (4, "刘女士", "刘思远", 8, "beginner", "weekend", "consulting", "2026-07-15 14:00"),
    (5, "赵先生", "赵子涵", 11, "intermediate", "weekend", "trial_booked", "2026-08-29 16:00"),
    (6, "孙女士", "孙一鸣", 9, "foundation", "weekend", "enrolled", "2026-08-01 10:30"),
    (7, "周先生", "周雨桐", 10, "beginner", "weekend", "lost", "2026-08-05 15:00"),
    (8, "吴女士", "吴泽宇", 8, "beginner", "weekend", "lost", "2026-08-08 13:00"),
    (9, "陈先生", "陈子墨", 12, "advanced", "weekday evening", "trial_completed", "2026-08-12 17:00"),
    (10, "杨女士", "杨晨曦", 6, "beginner", "weekend", "trial_booked", "2026-08-30 12:00"),
    (11, "黄先生", "黄子航", 13, "advanced", "weekend", "enrolled", "2026-08-03 16:30"),
    (12, "何女士", "何乐", 7, "beginner", "weekend", "new", "2026-09-02 10:00"),
]

TRIALS = [
    (1, 1, 7, "2026-08-23 14:00", "completed", 4.8, "孩子适应很好，基础动作学习积极。"),
    (2, 2, 2, "2026-08-22 18:30", "completed", 4.9, "课堂参与度高，喜欢教练的指导。"),
    (3, 5, 8, "2026-09-06 16:00", "booked", None, None),
    (4, 6, 7, "2026-08-09 14:00", "completed", 4.7, "已完成试听并确认报名。"),
    (5, 9, 5, "2026-08-16 19:00", "completed", 4.2, "具备竞赛基础，适合继续观察。"),
    (6, 10, 6, "2026-09-05 09:00", "booked", None, None),
    (7, 11, 10, "2026-08-10 15:00", "completed", 4.8, "比赛训练节奏合适，家长确认报名。"),
]

INTERACTIONS = [
    (1, 1, "wechat", "9岁以前没学过，可以上吗？", "2026-08-20 10:05"),
    (2, 1, "wechat", "我们周六下午比较方便。", "2026-08-21 09:20"),
    (3, 1, "phone", "试听感觉不错，孩子愿意继续学。", "2026-08-23 16:10"),
    (4, 1, "wechat", "课程挺合适，就是价格有点超预算。", "2026-08-23 18:30"),
    (5, 2, "wechat", "孩子很喜欢教练，想报名。", "2026-08-22 20:00"),
    (6, 2, "phone", "周二晚上的班和学校课程冲突。", "2026-08-23 09:30"),
    (7, 2, "wechat", "周末还有同级别的班吗？", "2026-08-23 10:00"),
    (8, 2, "wechat", "时间合适的话我们就报名。", "2026-08-23 10:10"),
    (9, 3, "wechat", "孩子7岁，想了解工作日晚上的启蒙课。", "2026-09-01 09:35"),
    (10, 3, "phone", "先帮我留意一下合适的时间。", "2026-09-01 11:00"),
    (11, 4, "wechat", "先了解一下8岁零基础有哪些课程。", "2026-07-15 14:10"),
    (12, 4, "wechat", "我再和家里商量一下。", "2026-07-16 10:00"),
    (13, 5, "wechat", "孩子有一点基础，周末下午可以试听吗？", "2026-08-29 16:10"),
    (14, 5, "phone", "好的，先预约周六16点试听。", "2026-08-30 10:30"),
    (15, 6, "wechat", "试听后孩子很喜欢基础班的氛围。", "2026-08-09 16:00"),
    (16, 6, "phone", "我们确认报名周六下午的课程。", "2026-08-10 09:00"),
    (17, 6, "wechat", "学费已了解，后续请安排开课提醒。", "2026-08-10 09:20"),
    (18, 7, "wechat", "课程内容合适，但2600元超出我们的预算。", "2026-08-06 10:00"),
    (19, 7, "phone", "这次先不报了，谢谢。", "2026-08-07 15:30"),
    (20, 7, "wechat", "如果有更优惠的课程再联系我。", "2026-08-08 09:00"),
    (21, 8, "wechat", "门店离家太远，接送确实不方便。", "2026-08-09 13:30"),
    (22, 8, "phone", "我们先不安排试听了。", "2026-08-09 17:00"),
    (23, 9, "wechat", "孩子参加过校队，想了解竞赛班训练。", "2026-08-12 17:10"),
    (24, 9, "phone", "试听节奏可以，我们再考虑一下。", "2026-08-16 20:00"),
    (25, 10, "wechat", "6岁刚开始接触乒乓球，周六上午方便。", "2026-08-30 12:10"),
    (26, 10, "phone", "请帮忙预约下周六的试听。", "2026-08-31 10:00"),
    (27, 11, "wechat", "孩子想提高比赛战术，周日下午方便。", "2026-08-03 16:40"),
    (28, 11, "phone", "试听满意，确认报名竞赛班。", "2026-08-10 17:00"),
    (29, 11, "wechat", "请把上课准备事项发给我。", "2026-08-11 09:00"),
    (30, 12, "wechat", "孩子7岁，周日上午的启蒙班还有位置吗？", "2026-09-02 10:10"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS coaches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    gender TEXT NOT NULL,
    specialty TEXT NOT NULL,
    level TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age_min INTEGER NOT NULL,
    age_max INTEGER NOT NULL,
    level TEXT NOT NULL,
    price INTEGER NOT NULL,
    lessons INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,
    weekday TEXT NOT NULL,
    start_time TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    enrolled INTEGER NOT NULL CHECK (enrolled >= 0 AND enrolled <= capacity),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (coach_id) REFERENCES coaches(id)
);
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    parent_name TEXT NOT NULL,
    child_name TEXT NOT NULL,
    child_age INTEGER NOT NULL,
    level TEXT NOT NULL,
    preferred_time TEXT,
    status TEXT NOT NULL CHECK (status IN ('new', 'consulting', 'trial_booked', 'trial_completed', 'enrolled', 'lost')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trials (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    trial_time TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('booked', 'completed', 'cancelled')),
    rating REAL CHECK (rating IS NULL OR rating BETWEEN 1.0 AND 5.0),
    note TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('wechat', 'phone', 'in_store')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
"""


def print_counts(conn):
    print("CoachFlow database ready.")
    for table in ("coaches", "courses", "classes", "leads", "trials", "interactions"):
        print(f"{table}: {conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]}")


def main():
    Path(DB_PATH).parent.mkdir(exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM coaches").fetchone()[0]:
            conn.execute("UPDATE leads SET preferred_time = 'weekend' WHERE id = 2")
            print_counts(conn)
            return
        conn.executemany("INSERT INTO coaches VALUES (?, ?, ?, ?, ?)", COACHES)
        conn.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?)", COURSES)
        conn.executemany("INSERT INTO classes VALUES (?, ?, ?, ?, ?, ?, ?)", CLASSES)
        conn.executemany("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?)", LEADS)
        conn.executemany("INSERT INTO trials VALUES (?, ?, ?, ?, ?, ?, ?)", TRIALS)
        conn.executemany("INSERT INTO interactions VALUES (?, ?, ?, ?, ?)", INTERACTIONS)
        print_counts(conn)


if __name__ == "__main__":
    main()
