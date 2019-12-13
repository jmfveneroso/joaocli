#!/usr/bin/python3

import argparse

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
}

queries = {
  'colab': 'colab',
  'ranklab': 'ranklab',
  'boqweb': 'boqrun',
  'boqrun': 'boqrun',
  'argparse': 'argparse',
  'ln': 'ln',
  'delete client': 'delete_client',
}

if __name__ == '__main__':
  parser = argparse.ArgumentParser(prog='joaocli', description='Command line interface for Joao.')

  parser.add_argument('--version', action='version', version='%(prog)s 0.1')

  parser.add_argument(
    'command', type=str, nargs='+', help='the main command'
  )

  args = parser.parse_args()

  main_command = args.command[0]
  q = queries[main_command]
  print(knowledge_points[q])

