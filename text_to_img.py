TMPL = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>解密结果</title>
    <style>
        @font-face {
            font-family: "Zpix";
            src: url("https://cdn.jsdelivr.net/gh/SolidZORO/zpix-pixel-font@latest/dist/zpix.ttf") format("truetype");
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        /* 全局黑底 + 像素等宽字体 */
        body {
            background: #000;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: "Zpix", Consolas, "Courier New", monospace;
            color: #ffffff;
        }

        .screen-container {
            width: 580px;
        }

        /* 顶部红色标题栏 */
        .title-bar {
            background: #ff0302;
            color: #000000;
            text-align: center;
            padding: 5px 0;
            font-size: 24px;
            margin-bottom: 18px;
        }

        /* 统计列表 */
        .stats-list {
            list-style: none;
            font-size: 22px;
            line-height: 1.65;
            margin-bottom: 16px;
        }

        .stats-list li {
            display: flex;
        }

        .stats-label::after {
            content: ":";
            margin-right: 4px;
        }

        /* 结局行的 value 使用指定颜色 */
        .stats-list li.ending-item .stats-value {
            color: #c63605;
        }

        /* 分割线 */
        .divider {
            height: 1px;
            background: #555;
            position: relative;
            margin-bottom: 10px;
        }

        /* 分割线中间红色标记点 */
        .divider::after {
            content: "";
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 200px;
            height: 2px;
            background: #c63605;
        }
    </style>
</head>
<body>
    <div class="screen-container">
        <!-- 顶部标题 -->
        <div class="title-bar">{{ title }}</div>

        <!-- 游戏统计数据（含结局） -->
        <ul class="stats-list">
            {% for item in stats %}
            <li>
                <span class="stats-label">{{ item.label }}</span>
                <span class="stats-value">{{ item.value }}</span>
            </li>
            {% endfor %}
            <li class="ending-item">
                <span class="stats-label">预测结局</span>
                <span class="stats-value">{{ ending_name }}</span>
            </li>
        </ul>

        <!-- 分割线 -->
        <div class="divider"></div>
    </div>
</body>
</html>
"""

def parse_analyse(analyse: str) -> dict:

    # 将 analyse 字符串转换为模板需要的字典格式。

    stats = []
    ending_name = ""

    for line in analyse.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 按中文冒号分割，只分一次
        if "：" not in line:
            continue
        label, value = line.split("：", 1)
        label = label.strip()
        value = value.strip()

        if label == "预测结局":
            ending_name = value
        else:
            stats.append({"label": label, "value": value})

    return {"title": "解密结果", "stats": stats, "ending_name": ending_name}


def text_to_img(self,analyse):
    img = self.html_render(
        TMPL,
        parse_analyse(analyse),
        options={
            "quality": 100,
            "device_scale_factor_level": "normal",
            "full_page": True,
            "omit_background": False,
            "type": "jpeg",
        },
    )
    return img
