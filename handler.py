from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from pathlib import Path
import os
import requests

def main(event, context):
        
    chromedriver_path = '/opt/chromedriver'
    o = Options()
    o.binary_location = '/opt/headless-chromium'
    o.add_argument('--headless')
    o.add_argument('--disable-gpu')
    o.add_argument('--no-sandbox')
    o.add_argument("--window-size=1280x1696")
    o.add_argument("--disable-application-cache")
    o.add_argument("--disable-infobars")
    o.add_argument("--hide-scrollbars")
    o.add_argument("--enable-logging")
    o.add_argument("--log-level=0")
    o.add_argument("--single-process")
    o.add_argument("--ignore-certificate-errors")
    o.add_argument("--homedir=/tmp")

    # ダウンロード用の設定
    driver = webdriver.Chrome(chromedriver_path, options=o)

    dldir_name = '/tmp/download'  # 保存先フォルダ名
    dldir_path = Path(dldir_name)
    dldir_path.mkdir(exist_ok=True)  # 存在していてもOKとする（エラーで止めない）
    download_dir = str(dldir_path.resolve())  # 絶対パス

    driver.command_executor._commands["send_command"] = (
        "POST",
        '/session/$sessionId/chromium/send_command'
    )
    params = {
        'cmd': 'Page.setDownloadBehavior',
        'params': {
            'behavior': 'allow',
            'downloadPath': download_dir
        }
    }
    driver.execute("send_command", params=params)

    target_url = os.environ['TARGET_URL']
    worker_id = os.environ['WORKER_ID']
    password = os.environ['PASSWORD']
    token = os.environ['SLACK_TOKEN']
    slack_channel = os.environ['SLACK_CHANNEL_ID']

    try:
        #　ページを開く
        driver.get(target_url)
        print(driver.title)

        # フォームに社員番号を入力してボタンをクリック
        id_form = driver.find_element_by_id('OBCID')
        id_form.send_keys(worker_id)
        driver.find_element_by_id('checkAuthPolisyBtn').click()
        sleep(1)

        # フォームにパスワードを入力してボタンをクリック
        pass_form = driver.find_element_by_id('Password')
        pass_form.send_keys(password)
        driver.find_element_by_id('login').click()
        sleep(3)

        # 会社名を出力
        company_name = driver.find_element_by_id('selectedTenantName').text
        print(company_name)

        # 最新の給与明細をダウンロード
        driver.find_element_by_xpath('//*[@id="js-payStatementTable"]/tbody/tr[1]/td[1]/button').click()
        sleep(5)

        # 給与明細PDFのパスを取得
        print(os.listdir('/tmp/download'))
        file = os.listdir('/tmp/download')[0]

        # ログアウトする
        driver.find_element_by_id('accountBtn').click()
        driver.find_element_by_xpath('//*[@id="accountBtn"]/div[2]/div/div[5]/a').click()
        sleep(2)

    except Exception as e:
        print("webdriverでエラー")
        print(e)

        return {
            'statusCode': 500,
            'body': "Error occured\n",
            'isBase64Encoded': False
        }

    driver.quit()

    try:
        # Slackにファイルアップロード
        files = {'file': open('/tmp/download/'+file, 'rb')}
        param = {
            'token': token,
            'channels': slack_channel, 
            'filename': Path(file).name,
            'initial_comment': '給与明細',
            'title:': '給与明細が届きました'
        }

        requests.post(url="https://slack.com/api/files.upload", params=param, files=files)
    except Exception as e:
        print("Slackへの投稿でエラー")
        print(e)

        return {
            'statusCode': 500,
            'body': "Error occured\n",
            'isBase64Encoded': False
        }

    return {
        'statusCode': 200,
        'body': "succeeded\n",
        'isBase64Encoded': False
    }