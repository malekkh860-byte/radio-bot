from flask import Flask, render_template_string

app = Flask(__name__)

index_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>الراديو المباشر</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #121212; color: #fff; text-align: center; padding-top: 50px; }
        h1 { color: #1db954; }
        a { color: #4e9af1; text-decoration: none; font-size: 18px; }
        .box { background: #1e1e1e; padding: 20px; border-radius: 10px; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>مرحباً بك في الراديو</h1>
    <div class="box">
        <p>البث يعمل على مدار الساعة بنجاح.</p>
        <br>
        <a href="/host">الذهاب إلى لوحة تحكم المذيع</a>
    </div>
</body>
</html>
"""

host_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة تحكم المذيع</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #1a1a1a; color: #fff; text-align: center; padding-top: 50px; }
        h1 { color: #f39c12; }
        a { color: #ff5252; text-decoration: none; font-size: 18px; }
        .box { background: #2a2a2a; padding: 20px; border-radius: 10px; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>لوحة تحكم المذيع</h1>
    <div class="box">
        <p>أهلاً بك في لوحة تحكم البث.</p>
        <br>
        <a href="/">العودة إلى الصفحة الرئيسية للراديو</a>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(index_html)

@app.route('/host')
def host_panel():
    return render_template_string(host_html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
  
