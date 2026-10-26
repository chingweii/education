import sqlite3
from flask import Flask, render_template, request, jsonify
from init_db import setup_database

app = Flask(__name__)
DB_NAME = "tutoring.db"

# Default password for admin dashboard access
ADMIN_PASSWORD = "admin123"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# FAQ Knowledge Base Rules - ONLY answer strictly from here
FAQ_RULES = {
    "fees": [
        "小学 RM280/月，中学 RM350/月，报名费 RM50。",
        "学费可以通过银行转账或现金支付，请在每月 5 号前完成缴费。"
    ],
    "schedule": [
        "我们的上课时间为：周一至周五 2pm–8pm，周六 9am–1pm，周日休息。"
    ],
    "courses": [
        "科目包含：国文、英文、数学、科学；中学阶段另提供历史、地理课程。",
        "我们的课程涵盖 7 至 17 岁（小学至中学阶段）的学生。"
    ],
    "class_size": [
        "为了保证教学质量，我们采用小班制，每班最多 12 人。"
    ],
    "trial": [
        "我们提供 1 次免费试课，但需要提前预约时间。"
    ],
    "absent": [
        "如需请假请提前一天通知，每人每月最多可安排 2 次补课。"
    ],
    "bus": [
        "抱歉，我们目前不提供校车接送服务。"
    ]
}

def analyze_and_draft_reply(question):
    q = question.strip()
    categories = []
    replies = []
    needs_human = 0
    matched = False

    # 1. Fee Inquiry
    if any(k in q for k in ["多少钱", "学费", "费用", "收费", "报名费", "转账", "现金", "付款", "缴费"]):
        matched = True
        categories.append("收费")
        replies.append("【学费说明】" + " ".join(FAQ_RULES["fees"]))

    # 2. Schedule Inquiry
    if any(k in q for k in ["时间", "几点", "营业", "周末", "星期", "几时", "开门", "放学", "休息"]):
        matched = True
        categories.append("时间")
        replies.append("【时间安排】" + " ".join(FAQ_RULES["schedule"]))

    # 3. Course / Subject Inquiry
    if any(k in q for k in ["科目", "课程", "教什么", "历史", "地理", "科学", "数学", "英文", "国文", "年龄", "岁", "年级"]):
        matched = True
        categories.append("课程")
        replies.append("【课程与适用年龄】" + " ".join(FAQ_RULES["courses"]))

    # 4. Trial Lesson
    if any(k in q for k in ["试课", "免费", "体验"]):
        matched = True
        if "课程" not in categories: categories.append("课程")
        replies.append("【免费试课】" + " ".join(FAQ_RULES["trial"]))

    # 5. Class Size
    if any(k in q for k in ["多少人", "人数", "小班", "班级"]):
        matched = True
        if "课程" not in categories: categories.append("课程")
        replies.append("【班级人数】" + " ".join(FAQ_RULES["class_size"]))

    # 6. Absence / Makeup Lessons
    if any(k in q for k in ["请假", "补课", "缺席"]):
        matched = True
        if "其他" not in categories and not categories: categories.append("其他")
        replies.append("【请假规则】" + " ".join(FAQ_RULES["absent"]))

    # 7. Bus / Transport
    if any(k in q for k in ["校车", "接送", "巴士", "交通"]):
        matched = True
        if "其他" not in categories and not categories: categories.append("其他")
        replies.append("【校车接送】" + " ".join(FAQ_RULES["bus"]))

    # Strict fallback check for unlisted questions (No hallucinations allowed)
    unknown_keywords = ["折扣", "优惠", "地址", "老师", "位置", "怎么去", "电话", "找谁", "校长", "回扣", "便宜", "停车场", "伙食"]
    if not matched or any(k in q for k in unknown_keywords):
        needs_human = 1
        if not categories:
            categories.append("其他")
        replies.append("⚠️ FAQ 中未涵盖此问题的解答，必须由教务人员人工处理回复。")

    cat_str = " / ".join(list(dict.fromkeys(categories))) if categories else "其他"
    reply_str = "\n".join(replies)

    return cat_str, reply_str, needs_human

@app.route("/")
def parent_portal():
    return render_template("index.html")

@app.route("/admin")
def admin_portal():
    return render_template("admin.html")

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json or {}
    pwd = data.get("password", "")
    if pwd == ADMIN_PASSWORD:
        return jsonify({"success": True, "message": "验证成功"})
    return jsonify({"success": False, "message": "密码错误，拒绝访问！"}), 401

@app.route("/api/inquire", methods=["POST"])
def submit_inquiry():
    data = request.json or {}
    parent_name = data.get("parent_name", "").strip()
    phone = data.get("phone", "").strip()
    branch = data.get("branch", "").strip()
    try:
        child_age = int(data.get("child_age", 0))
    except (ValueError, TypeError):
        child_age = 0
    question = data.get("question", "").strip()

    if not parent_name or not phone or not branch or not question or child_age <= 0:
        return jsonify({"success": False, "message": "请填写所有必填信息！"}), 400

    category, draft_reply, needs_human = analyze_and_draft_reply(question)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inquiries (parent_name, phone, branch, child_age, question, category, draft_reply, needs_human)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (parent_name, phone, branch, child_age, question, category, draft_reply, needs_human))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "提交成功！您的咨询已送达课程顾问。"})

@app.route("/api/admin/inquiries", methods=["GET"])
def get_inquiries():
    branch = request.args.get("branch", "all")
    conn = get_db_connection()
    cursor = conn.cursor()

    if branch in ["SS2", "SS15"]:
        cursor.execute("SELECT * FROM inquiries WHERE branch = ? ORDER BY id DESC", (branch,))
    else:
        cursor.execute("SELECT * FROM inquiries ORDER BY id DESC")
    
    rows = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM inquiries")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM inquiries WHERE needs_human = 1 AND status = 'pending'")
    needs_human_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "success": True,
        "total": total_count,
        "needs_human_total": needs_human_count,
        "data": [dict(row) for row in rows]
    })

@app.route("/api/admin/approve/<int:inquiry_id>", methods=["POST"])
def approve_inquiry(inquiry_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE inquiries SET status = 'approved', needs_human = 0 WHERE id = ?", (inquiry_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "已批准该笔回复！"})

if __name__ == "__main__":
    setup_database()
    print("==================================================")
    print("🚀 智达补习中心管理系统已启动")
    print("📌 家长前台咨询入口: http://127.0.0.1:5002")
    print("📌 机构教务管理后台 (带密码防护): http://127.0.0.1:5002/admin")
    print("🔑 默认后台登录密码: admin123")
    print("==================================================")
    app.run(host="0.0.0.0", port=5002, debug=True)