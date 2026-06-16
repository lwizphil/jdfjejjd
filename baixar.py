import io
import os
import re
import threading

from concurrent.futures import ThreadPoolExecutor

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

DOWNLOAD_FOLDER = "downloads"
LINKS_FILE = "links.txt"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


thread_local = threading.local()


def get_service():
    """
    Cada thread cria sua própria conexão com a API.
    Isso evita o erro 'free(): corrupted unsorted chunks'.
    """

    if not hasattr(thread_local, "service"):

        credentials = service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=SCOPES,
        )

        thread_local.service = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    return thread_local.service


def extrair_id(link):

    padroes = [
        r"id=([A-Za-z0-9_-]+)",
        r"/d/([A-Za-z0-9_-]+)",
    ]

    for p in padroes:

        m = re.search(p, link)

        if m:
            return m.group(1)

    return None


def baixar(link):

    file_id = extrair_id(link)

    if not file_id:
        print("Link inválido:", link)
        return

    service = get_service()

    try:

        metadata = service.files().get(
            fileId=file_id,
            fields="name,size"
        ).execute()

        nome = metadata["name"]

        caminho = os.path.join(DOWNLOAD_FOLDER, nome)

        request = service.files().get_media(fileId=file_id)

        fh = io.FileIO(caminho, "wb")

        downloader = MediaIoBaseDownload(fh, request)

        done = False

        while not done:

            status, done = downloader.next_chunk()

        fh.close()

        print(f"✔ {nome}")

    except Exception as e:

        print(f"❌ {file_id}")

        print(e)


def main():

    with open(LINKS_FILE, encoding="utf8") as f:

        links = [
            linha.strip()
            for linha in f
            if linha.strip()
        ]

    print(f"Foram encontrados {len(links)} links.")

    with ThreadPoolExecutor(max_workers=8) as executor:

        executor.map(baixar, links)

    print("Downloads finalizados.")


if __name__ == "__main__":
    main()
