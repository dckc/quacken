import json
import pprint

def explore(fp):
    x = json.load(fp)
    pprint.pprint(x)

def main(argv):
    fn = argv[1]
    fp = open(fn)
    explore(fp)

if __name__ == '__main__':
    import sys
    main(sys.argv)
