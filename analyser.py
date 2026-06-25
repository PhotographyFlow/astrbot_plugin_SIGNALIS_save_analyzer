import requests
from .decoder import png_to_json
import json


# 秒转换为 时：分：秒
def seconds_to_hms(total_seconds):
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# 检查计算死亡次数的参数是否有效
def is_valid_elster_status(s: str) -> bool:
    if not s.endswith("-"):
        return False
    parts = s.split("-")
    # 16 个数字 + 1 个末尾空串
    if len(parts) != 17:
        return False
    # 检查前 16 项
    return all(p in ("0", "1", "2") for p in parts[:16])


def analyser(url, local_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    json_str = png_to_json(path=local_path, indent=2)
    data = json.loads(json_str)

    # ints
    ints_data = data.get("ints", {})
    damage = ints_data.get("TotalDamage", "error")
    kills = ints_data.get("Kills", "error")
    shots_fired = ints_data.get("ShotsFired", "error")
    phoenix = ints_data.get("Phoenix", "error")  # 死里逃生次数
    npc_talks = ints_data.get("E_NPC", "error")
    door = ints_data.get("E_Door", "error")

    # floats
    floats_data = data.get("floats", {})
    total_game_time_sec = floats_data.get("TotalGametimeSeconds", "error")
    total_non_game_sec = floats_data.get("TotalNonSeconds", "error")
    false_ending_time_sec = floats_data.get("E_Mem", "error")  # 伪结局游玩时间
    regen_time_sec = floats_data.get("Regen", "error")
    heal_T = floats_data.get("E_HealT", "error")
    heal_TH = floats_data.get("E_HealTH", "error")  # 高血量时间比 = heal_T / heal_TH
    # 将时间由秒转换为 时：分：秒
    if isinstance(false_ending_time_sec, (float)):
        false_ending_time_hms = seconds_to_hms(false_ending_time_sec)
    else:
        false_ending_time_hms = "error"

    if (
        isinstance(total_game_time_sec, (float))
        and isinstance(total_non_game_sec, (float))
        and total_game_time_sec > total_non_game_sec
    ):
        active_game_sec = total_game_time_sec - total_non_game_sec
        total_game_time_hms = seconds_to_hms(total_game_time_sec)
        active_game_hms = seconds_to_hms(active_game_sec)
    else:
        total_game_time_hms = "error"
        active_game_hms = "error"

    if isinstance(regen_time_sec, (float)):
        regen_time_hms = seconds_to_hms(regen_time_sec)
    else:
        regen_time_hms = "error"

    # 计算高血量时间比
    if (
        isinstance(heal_T, (float))
        and isinstance(heal_TH, (float))
        and heal_TH < heal_T
    ):
        healed_time_fraction = int(round(heal_TH / heal_T, 2) * 100)
    else:
        healed_time_fraction = "error"

    # strings
    strings_data = data.get("strings", {})
    lstr_frame_status = strings_data.get("ElsterFrameStatus", "error")
    if is_valid_elster_status(lstr_frame_status):
        death = lstr_frame_status.count(
            "2"
        )  # 死亡次数判定，计数有多少个2，少于16时应该是确定的
        if death == 16:
            death = "16或更多"
    else:
        death = "error"

    # 结局预测
    # 初始结局点数
    e_circle = 2
    e_death = 0
    e_leave = 0
    # 先检查所有需要的参数是否有效，然后计算结局点数
    if (
        total_game_time_hms != "error"
        and npc_talks != "error"
        and healed_time_fraction != "error"
        and regen_time_hms != "error"
        and damage != "error"
        and phoenix != "error"
        and death != "error"
        and kills != "error"
        and false_ending_time_hms != "error"
    ):
        # 游戏时间，小于6h +2 circle，6-12h nothing，大于12h +1 death
        if active_game_sec < 21600.0:
            e_circle += 2
        elif active_game_sec > 43200.0:
            e_death += 1

        # npc互动次数，25-35 +1 leave，大于35 +2 leave
        if npc_talks > 35:
            e_leave += 2
        elif npc_talks > 25 and npc_talks <= 35:
            e_leave += 1

        # 高血量时间比，大于60 +1 leave，大于80 +2 leave
        if healed_time_fraction > 80:
            e_leave += 2
        elif healed_time_fraction > 60 and healed_time_fraction <= 80:
            e_leave += 1

        # 自动回血时间，大于5min +2 death
        if regen_time_sec > 300.0:
            e_death += 2

        # 死里逃生次数，大于8 +1 death
        if phoenix > 8:
            e_death += 2

        # 杀敌数，90-120 +1 death，大于120 +2 death
        if kills > 120:
            e_death += 2
        elif kills > 90 and kills <= 120:
            e_death += 1

        # 伪结局游玩时间，大于5min +1 leave
        if false_ending_time_sec > 300.0:
            e_leave += 1

        # 互动故障门数量，大于40 +1 leave
        if door > 40:
            e_leave += 1

    # 通过结局点数预测结局
    if e_leave == e_circle or e_death == e_circle or e_leave == e_death:
        ending = "回忆"
    else:
        max_val = max(e_circle, e_death, e_leave)
        if e_circle == max_val:
            ending = "回忆"
        elif e_death == max_val:
            ending = "诺言"
        else:
            ending = "离去"

    analyse = f"游戏总时长：{total_game_time_hms}\n游戏活跃时长：{active_game_hms}\n伪结局游玩时间：{false_ending_time_hms}\n杀敌数：{kills}\n开火数：{shots_fired}\n死里逃生次数：{phoenix}\n高血量时间比：{healed_time_fraction}%\n承受伤害：{damage}\n死亡次数：{death}\nNPC互动次数：{npc_talks}\n互动故障门数量：{door}\n预测结局：{ending}"

    # 用完删除存档图片
    local_path.unlink()

    # 返回解析文本
    return analyse
