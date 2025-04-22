from flask import Flask, request
import mido
from mido import Message
import threading
import time

app = Flask(__name__)

# ReaderごとのUID→CCマッピング
reader_uid_to_cc = {
    "1": {
        "04:94:6a:5a:a3:11:90": 21,
        "04:8d:6a:5a:a3:11:90": 22,
        "04:19:6a:5a:a3:11:90": 25,
    },
    "2": {
        "04:94:6a:5a:a3:11:90": 23,
        "04:8d:6a:5a:a3:11:90": 24,
        "04:19:6a:5a:a3:11:90": 26,
    },
}

# MIDI出力ポートを開きます
# お使いの環境に合わせてポート名を変更してください
midi_out = mido.open_output("IAC„Éâ„É©„Ç§„Éê Ableton MIDI In")

# ReaderごとにアクティブなUIDを管理する辞書を新しく定義します
# 各reader IDをキーとし、値はそのreaderで現在アクティブなUIDのセットとします
active_uids_by_reader = {"1": set(), "2": set()}

# 各UIDの現在のCC値を管理する辞書と、目標値を管理する辞書
current_values = {}
# CC値のフェードイン/アウトのステップサイズ
fade_step = 2


# CC値を滑らかに変化させる関数
def fade_cc(uid, cc, target_value):
    # UIDに関連付けられた現在のCC値を取得、なければ0から開始
    current = current_values.get(uid, 0)
    # このUIDの目標値を設定
    current_values[f"{uid}_target"] = target_value

    # 目標値までの方向を決定
    direction = 1 if target_value > current else -1
    # 目標値までのステップ数を計算
    steps = abs(target_value - current) // fade_step
    # ステップ数が0の場合（すでに目標値か、目標値との差がステップサイズ未満）
    if steps == 0:
        # 目標値を直接送信
        midi_out.send(
            Message("control_change", channel=9, control=cc, value=target_value)
        )
        # 現在値を更新
        current_values[uid] = target_value
        return  # 関数終了

    # フェードの持続時間を設定（目標値が127なら2秒、そうでなければ5秒）
    fade_duration = 2.0 if target_value == 127 else 5.0
    # 各ステップの時間を計算
    step_time = fade_duration / steps

    # ステップごとにCC値を更新して送信
    for i in range(steps + 1):
        # フェード中に目標値が変わった場合は、このフェード処理を中断
        if current_values.get(f"{uid}_target") != target_value:
            return
        # 次のステップのCC値を計算
        val = current + i * fade_step * direction
        # CC値の範囲（0〜127）に収まるように調整
        val = max(0, min(127, val))
        # MIDIメッセージを送信
        midi_out.send(Message("control_change", channel=9, control=cc, value=val))
        # 現在値を更新
        current_values[uid] = val
        # 次のステップまで待機
        time.sleep(step_time)

    # フェード完了後、最終的な現在値を目標値に設定
    current_values[uid] = target_value


# /nfc エンドポイントへのリクエストを処理する関数
@app.route("/nfc")
def handle_nfc():
    # リクエストパラメータからuidとreaderを取得
    uid = request.args.get("uid")
    reader = request.args.get(
        "reader", "1"
    )  # readerパラメータがない場合はデフォルトで"1"

    print(f"📡 受信: {uid} (reader {reader})")

    # リクエスト元のreaderが管理対象に含まれているか確認し、なければセットを作成
    if reader not in active_uids_by_reader:
        active_uids_by_reader[reader] = set()

    # UIDが"none"の場合（タグがReaderから離れたことを示す）
    if uid == "none":
        # そのreaderに関連付けられている全てのアクティブなUIDを取得し、リストをコピー
        if reader in active_uids_by_reader:
            # そのreaderに関連付けられているアクティブなUIDのリストをコピーしてループ
            for active_uid in list(active_uids_by_reader[reader]):
                # アクティブなUIDに対応するCC値が定義されているか確認
                cc = reader_uid_to_cc.get(reader, {}).get(active_uid)
                if cc is not None:
                    # 目標値を0に設定し、フェードアウト処理を開始
                    current_values[f"{active_uid}_target"] = 0
                    print(f"🛑 タグ離脱 → reader {reader} CC {cc} = 0 (フェードアウト)")
                    threading.Thread(
                        target=fade_cc, args=(active_uid, cc, 0), daemon=True
                    ).start()
            # そのreaderに関連付けられている全てのアクティブUIDをクリア
            active_uids_by_reader[reader].clear()
        return "OK"  # 処理完了を返す

    # UIDに対応するCC値を取得 (readerとuidに対応する定義がない場合はNone)
    cc = reader_uid_to_cc.get(reader, {}).get(uid)

    # UIDがディクショナリに定義されており (cc is not None)、
    # かつ、そのreaderでまだアクティブでないか (uid not in active_uids_by_reader[reader]) を確認
    if cc is not None and uid not in active_uids_by_reader[reader]:
        # 新しいタグ検出時の処理
        current_values[f"{uid}_target"] = (
            0  # 初期目標値を0に設定（フェードイン開始のため）
        )
        print(f"✅ タグ検出 → reader {reader} CC {cc} = 127 (フェードイン)")
        # 目標値を127に設定し、フェードイン処理をスレッドで開始
        threading.Thread(target=fade_cc, args=(uid, cc, 127), daemon=True).start()
        # UIDをそのreaderのアクティブセットに追加
        active_uids_by_reader[reader].add(uid)
    else:
        # 条件を満たさなかった場合（未定義のUID、または既にアクティブなUID）
        # エラーメッセージを、未定義かアクティブか区別するように改善して表示
        if cc is None:
            print(f"🔁 未定義のUID ({uid}) for reader {reader}")
        else:
            print(f"🔁 既にアクティブなUID ({uid}) for reader {reader}")

    return "OK"  # 処理完了を返す


# スクリプトが直接実行された場合の処理
if __name__ == "__main__":
    print("🌐 Flask MIDIサーバー起動中 (port 3000)...")
    # Flaskアプリケーションを起動
    # host='0.0.0.0' で外部からのアクセスも許可
    # port=3000 でポート番号を指定
    app.run(host="0.0.0.0", port=3000)
