#!/usr/bin/python3

from __future__ import print_function
import argparse
import io
import subprocess
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

def gdrive_authenticate():
  """
  Authenticate in Google Drive and store token.
  """
  creds = None
  # The file token.pickle stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists('token.pickle'):
      with open('token.pickle', 'rb') as token:
          creds = pickle.load(token)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
          creds.refresh(Request())
      else:
          flow = InstalledAppFlow.from_client_secrets_file(
              'credentials.json', SCOPES)
          creds = flow.run_local_server(port=0)
      # Save the credentials for the next run
      with open('token.pickle', 'wb') as token:
          pickle.dump(creds, token)

  service = build('drive', 'v3', credentials=creds)
  return service

def gdrive_download(file_id):
  service = gdrive_authenticate()

  request = service.files().export_media(fileId=file_id, mimeType='text/plain')
  fh = io.BytesIO()
  downloader = MediaIoBaseDownload(fh, request)
  done = False
  while done is False:
    status, done = downloader.next_chunk()

  bytes_io = fh.getvalue()
  content = bytes_io.decode('UTF-8')
  print(content)

  # Write to file.
  # with open("test.txt", "wb") as f:
  #   f.write(fh.getbuffer())

knowledge_points = {
  'colab': 'Colab (go/colab) is Google\'s Jupyter Notebook.',
  'ranklab': 'Ranklab is a kernel for Colab with a lot of predefined functions.',
  'boqweb': 'boq run --node=experimental/engedu/gti/projects/week20191202/nyc/team1/java/com/google/busyeats/ui,experimental/engedu/gti/projects/week20191202/nyc/team1/java/com/google/busyeats/service',
  'boqrun': 'boq run --node=experimental/engedu/gti/projects/week20191202/nyc/team1/java/com/google/busyeats/ui,experimental/engedu/gti/projects/week20191202/nyc/team1/java/com/google/busyeats/service',
  'argparse': 'https://docs.python.org/3/howto/argparse.html',
  'ln': 'ln -s FILE LINK',
  'delete_client': """
    g4d ${name}
    g4 revert ...
    g4 citc -d ${name}
  """,
  'jarvis': """
    jarvis_cli create <exp_id> --owner=<owner>
    https://g3doc.corp.google.com/knowledge/graph/jarvis/g3doc/user_guide/cli.md?cl=head
    For Hume: http://hume.google.com/exp/
  """,
  'osrp_eval': """
  https://g3doc.corp.google.com/knowledge/g3doc/osrp/development/evaluation.md?cl=head
  """,
  'eas': 'Eval Analytics Server',
  'dremel': 'Google\'s MySQL',
  'busyeats': 'experimental/engedu/gti/projects/week20191202/nyc/team1/java/com/google/busyeats',
  'chromeextensiongoogle': 'https://g3doc.corp.google.com/company/area120/common/g3doc/sets/chrome.md?cl=head',
  'ke': 'Knowledge Engine',
  'floormap': 'https://floorscope.googleplex.com/',
  'splitcl': 'https://yaqs.corp.google.com/eng/q/4599571930415104',
  'linesofcode': 'https://changestats.googleplex.com/',
  'iql': 'https://g3doc.corp.google.com/knowledge/answers/g3doc/iql.md?cl=head',
  'triggerfullpageosrp': """
    Queries with a &stick= parameter in the URL Sticky queries for 
    OSRP-eligible interpretations ignore the triggering algorithm and 
    always show a full-page OSRP.
  """,
  'chromeinsecure': '/opt/google/chrome/chrome --disable-web-security --user-data-dir ~/testing',
  'how_to_open_chrome_tab': '/opt/google/chrome/chrome --new-tab http://google.com',
  'how_to_open_chrome_window': '/opt/google/chrome/chrome --new-window http://google.com',
  'forcecollapsed': """
    Add to URL: expflags=Osrp__force_decision:BAILOUT
  """,
  'forcewholepage': """
    Add to URL: expflags=Osrp__force_decision:OSRP
  """,
  'disableosrp': """
    Add to URL: expflags=Osrp__force_decision:NOT_TRIGGERED
  """,
  'experimentflag': 'expflags=HealthConditions__enable_specific_symptom_tab:true',
  'searchdirectorycs': """
    "file:knowledge/kefi/card_config/card_configs/* intent_name="
  """,
  'payslips': 'http://go/gpayslips',
  'xpdeposit': """
    Tipo: TED para contas de mesma titularidade
    Banco: 102
    Agência: 0001
    Conta: 261233-6
    Favorecido: João Mateus de Freitas Veneroso
    CPF: 111.143.096-99
    ISPB (se for exigido): 02.332.886
  """,
  'create_drive_secret_key': """
    https://github.com/Cloudbox/Cloudbox/wiki/Google-Drive-API-Client-ID-and-Client-Secret
  """,
  'using drive api': """
    https://developers.google.com/drive/api/v3/quickstart/python
  """,
  'googledriveapi': """
    pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
  """,
}

queries = {
  'colab': 'colab',
  'ranklab': 'ranklab',
  'boqweb': 'boqrun',
  'boqrun': 'boqrun',
  'argparse': 'argparse',
  'ln': 'ln',
  'delete client': 'delete_client',
  'jarvis': 'jarvis',
  'osrp_eval': 'osrp_eval',
  'eas': 'eas',
  'dremel': 'dremel',
  'busyeats': 'busyeats',
  'busy eats': 'busyeats',
  'chrome extensions in google': 'chromeextensiongoogle',
  'ke': 'ke',
  'floormap': 'floormap',
  'how to split cl': 'splitcl',
  'floor map': 'floormap',
  'officemap': 'floormap',
  'office map': 'floormap',
  'linesofcode': 'linesofcode',
  'lines of code': 'linesofcode',
  'iql': 'iql',
  'intent query language': 'iql',
  'how to trigger a fullpage osrp': 'triggerfullpageosrp',
  'chromeinsecure': 'chromeinsecure',
  'jarvisui': 'jarvisui',
  'hume': 'jarvisui',
  'how to open tab from terminal': 'how_to_open_chrome_tab',
  'how to open window from terminal': 'how_to_open_chrome_window',
  'force collapsed osrp': 'force_collapsed',
  'force wholepage osrp': 'force_wholepage',
  'force collapsed': 'forcecollapsed',
  'force wholepage': 'forcewholepage',
  'force bailout': 'forcecollapsed',
  'disable osrp': 'disableosrp',
  'experiment flag': 'experimentflag',
  'how to search inside directory in code search': 'searchdirectorycs',
  'search inside directory in code search': 'searchdirectorycs',
  'search directory in code search': 'searchdirectorycs',
  'search directory in cs': 'searchdirectorycs',
  'cs search directory': 'searchdirectorycs',
  'payslips': 'payslips',
  'payment': 'payslips',
  'paycheck': 'payslips',
  'deposito na xp investimentos': 'xpdeposit',
  'deposito para a xp investimentos': 'xpdeposit',
  'deposito na xp': 'xpdeposit',
  'deposito para a xp': 'xpdeposit',
}

commands = {
  'jarvisui': ['/opt/google/chrome/chrome', '--new-tab', 'http://hume.google.com/exp/'],
}

if __name__ == '__main__':
  parser = argparse.ArgumentParser(prog='joaocli', description='Command line interface for Joao.')

  parser.add_argument('--version', action='version', version='%(prog)s 0.1')

  parser.add_argument(
    'command', type=str, nargs='+', help='the main command'
  )

  args = parser.parse_args()

  main_command = args.command[0]

  if main_command in queries:
    q = queries[main_command]
  elif main_command == 'google drive':
    file_id = '1MuaSM4kIRJ4Zz2iIViMOaaz3VG6iH9Q8YLzlXK40mfE'
    gdrive_download(file_id)
    quit()
  else:
    print('Not found')
    quit()

  if q in knowledge_points:
    print(knowledge_points[q])
  elif q in commands:
    subprocess.run(commands[q])

