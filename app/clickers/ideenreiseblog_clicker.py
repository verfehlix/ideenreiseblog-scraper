import os
from os import listdir
from os.path import isfile, join

import shutil
import time
import json

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from colorama.ansi import Style
from colorama import init, Fore
from bs4 import BeautifulSoup
from google_drive_downloader import GoogleDriveDownloader as gdd

init(autoreset=False)

# function to enable downloading of files
def enable_download_headless(browser, download_dir):
    browser.command_executor._commands["send_command"] = (
        "POST",
        "/session/$sessionId/chromium/send_command",
    )
    params = {
        "cmd": "Page.setDownloadBehavior",
        "params": {"behavior": "allow", "downloadPath": download_dir},
    }
    browser.execute("send_command", params)


# function to initialize chrome webdriver
def init_chrome_webdriver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--window-size=1920x1080")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--verbose")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option(
        "prefs",
        {
            "download.default_directory": " /mnt/c/Users/Felix/Downloads",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing_for_trusted_sources_enabled": False,
            "safebrowsing.enabled": False,
        },
    )

    driver = webdriver.Chrome(
        options=opts,
    )

    return driver


def check_before_download():
    # verify there are no files in the downloads folder
    assert len(os.listdir(download_dir)) == 0, "Downloads folder not empty!"


def check_after_download():
    # verify there is a new file in the downloads folder
    assert len(os.listdir(download_dir)) == 1, "Downloads folder does not contain file!"


def move_temp_file_to_finished(download_path, finished_dir, file_name, link_type):
    # rename & move file to "finished" folder
    style = Fore.BLACK

    if link_type == "gdrive":
        style = Fore.GREEN
    elif link_type == "dropbox":
        style = Fore.BLUE
    elif link_type == "hidrive":
        style = Fore.RED + Style.BRIGHT

    print(
        style
        + "\t\t\tMoving temp download file to: "
        + finished_dir
        + file_name
        + Style.RESET_ALL
    )
    os.makedirs(os.path.dirname(finished_dir), exist_ok=True)
    shutil.move(download_path, finished_dir + file_name)


def handle_single_gdrive_page(page, download_dir, finished_dir):
    check_before_download()

    # download file
    file_id = page.replace("https://drive.google.com/file/d/", "").split("/")[0]
    print(Fore.GREEN, end="\r")
    gdd.download_file_from_google_drive(
        file_id=file_id,
        dest_path=download_dir + "download.pdf",
    )

    # get filename
    r = requests.get(page)
    soup = BeautifulSoup(r.content, "html.parser")
    file_name = soup.text.split("-")[0].strip()

    # rename & move file to "finished" folder
    move_temp_file_to_finished(
        download_dir + "download.pdf", finished_dir, file_name, "gdrive"
    )

    print(Style.RESET_ALL)


def handle_single_dropbox_page(page, download_dir, finished_dir):
    check_before_download()

    # download file
    print(
        Fore.BLUE + "\t\t\tDownloading dropbox file into ./download/download.pdf...",
        end="",
    )
    headers = {"user-agent": "Wget/1.16 (linux-gnu)"}
    r = requests.get(page, stream=True, headers=headers)
    with open(download_dir + "download.pdf", "wb") as f:
        for chunk in r.iter_content(1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    print(" Done.")

    check_after_download()

    # get file name
    r = requests.get(page)
    soup = BeautifulSoup(r.content, "html.parser")
    file_name = soup.text.split("-")[1].strip()

    # rename & move file to "finished" folder
    move_temp_file_to_finished(
        download_dir + "download.pdf", finished_dir, file_name, "dropbox"
    )


def handle_single_hidrive_page(page, download_dir, finished_dir):

    # download file
    print(
        Fore.RED
        + Style.BRIGHT
        + "\t\t\tDownloading hidrive file into ./download/download.pdf...",
        end="",
    )

    # setup
    driver = init_chrome_webdriver()
    enable_download_headless(driver, download_dir)

    # open page
    driver.get(page)

    check_before_download()

    # check that we're on a HiDrive page
    assert "HiDrive" in driver.title, "'HiDrive' not found in page title. Aborting!"

    # get filename & download button
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".download-button"))
        )

        file_name = (
            driver.find_element_by_css_selector(".filename")
            .get_attribute("innerHTML")
            .replace("\u200b", "")
            .replace("\u200c", "")
        )

        element.click()
    finally:
        # exit
        time.sleep(5)
        driver.quit()
    print(" Done.")

    check_after_download()

    # determine name of downloaded file
    onlyfiles = [f for f in listdir(download_dir) if isfile(join(download_dir, f))]

    # rename & move file to "finished" folder
    move_temp_file_to_finished(
        download_dir + onlyfiles[0], finished_dir, file_name, "hidrive"
    )


def determine_page_type(link):
    link_type = "unknown"
    link_color = Fore.BLACK

    if link.startswith("https://my.hidrive.com"):
        link_type = "hidrive"
        link_color = Fore.RED + Style.BRIGHT
    elif link.startswith("https://www.dropbox.com"):
        link_type = "dropbox"
        link_color = Fore.BLUE
    elif link.startswith("https://drive.google.com"):
        link_type = "gdrive"
        link_color = Fore.GREEN

    assert link_type != "unknown", "Unkown link type for link: " + link + ". Aborting!"

    print(
        Style.RESET_ALL + "\t\tLink Type: " + link_color + link_type + Style.RESET_ALL
    )
    return link_type


def handle_single_list_entry(list_entry, index, total, download_dir, finished_dir):
    print(Style.RESET_ALL)

    name = list_entry["post"]
    links = list_entry["files"]

    link_links_text = "links" if len(links) > 1 else "link"

    print(
        Fore.MAGENTA
        + "["
        + str(index)
        + "/"
        + str(total)
        + "] "
        + Fore.WHITE
        + name
        + Style.RESET_ALL
        + " ("
        + str(len(links))
        + " "
        + link_links_text
        + "):"
    )

    for file_index, current_link in enumerate(links):
        print(
            Fore.YELLOW
            + "\tLink "
            + str(file_index + 1)
            + "/"
            + str(len(links))
            + Style.BRIGHT
            + ": "
            + str(current_link)
        )
        link_type = determine_page_type(current_link)

        if link_type == "hidrive":
            handle_single_hidrive_page(current_link, download_dir, finished_dir)
        elif link_type == "dropbox":
            handle_single_dropbox_page(current_link, download_dir, finished_dir)
        elif link_type == "gdrive":
            handle_single_gdrive_page(current_link, download_dir, finished_dir)

    print("")


def handle_file_list(file_list_path, download_dir, finished_dir):
    print(Style.RESET_ALL)
    print(Fore.WHITE + "starting clicker...")
    print(Fore.WHITE + "reading file '" + str(file_list_path) + "'")

    scraped_file = open(file_list_path)
    scraped_file_content = json.load(scraped_file)
    print(Fore.WHITE + "loaded " + str(len(scraped_file_content)) + " entries")

    for index, list_entry in enumerate(scraped_file_content):
        handle_single_list_entry(
            list_entry,
            index + 1,
            len(scraped_file_content),
            download_dir,
            finished_dir,
        )

    # first = scraped_file_content[0]
    # handle_single_list_entry(first, download_dir, finished_dir)


file_list_path = "test.json"

download_dir = "./download/"
finished_dir = "./finished/"

handle_file_list(file_list_path, download_dir, finished_dir)

# hidrive = "https://my.hidrive.com/lnk/ULH0qBaQ#file"
# handle_single_hidrive_page(hidrive, download_dir, finished_dir)

# dropbox = "https://www.dropbox.com/s/6b7lftucteksz44/Rechenmalblatt_HalbschriftlicheDivision.pdf?dl=0"
# handle_single_dropbox_page(dropbox, download_dir, finished_dir)

# gdrive = "https://drive.google.com/file/d/0BwRaLAdDYVR8QXBROU0zRF84YzQ/view?usp=sharing"
# handle_single_gdrive_page(gdrive, download_dir, finished_dir)
