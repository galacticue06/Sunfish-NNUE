#!/usr/bin/env pypy -u
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import division
import importlib
import re
import sys
import time
import logging
import argparse

import tools
import sunfish

from tools import WHITE, BLACK, Unbuffered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('module', help='sunfish.py file (without .py)', type=str, default='sunfish', nargs='?')
    parser.add_argument('--tables', metavar='pst', help='alternative pst table', type=str, default=None)
    args = parser.parse_args()

    sunfish = importlib.import_module(args.module)
    if args.tables is not None:
        pst_module = importlib.import_module(args.tables)
        sunfish.pst = pst_module.pst

    logging.basicConfig(filename='sunfish.log', level=logging.DEBUG)
    out = Unbuffered(sys.stdout)
    def output(line):
        print(line, file=out)
        logging.debug(line)
    pos = tools.parseFEN(tools.FEN_INITIAL)
    searcher = sunfish.Searcher()
    color = WHITE
    our_time, opp_time = 1000, 1000 # time in centi-seconds
    show_thinking = True

    stack = []
    nhist = []
    options_org = {"Hash": ["spin", 1, 1, 33554432],
               "Clear Hash": ["button"],
               "PolyglotBook": ["string", "<empty>"],
               "SyzygyPath": ["string", "<empty>"],
               "EvalRoughness": ["spin", 13, 4, 692]}
    
    while True:
        if stack:
            smove = stack.pop()
        else:
            smove = input()

        logging.debug(f'>>> {smove} ')

        if smove == 'quit':
            break

        elif smove == 'uci':
            output('id name Sunfish')
            output('id author Thomas Ahle & Contributors')

            for i in options_org:
                if len(options_org[i]) > 2:
                    output('option name {} type {} default {} min {} max {}'.format(i, options_org[i][0], options_org[i][1], options_org[i][2], options_org[i][3]))
                elif len(options_org[i]) == 2:
                    output('option name {} type {} default {}'.format(i, options_org[i][0], options_org[i][1]))
                else:
                    output('option name {} type {} '.format(i, options_org[i][0]))
            output('uciok')

        elif smove == 'isready':
            output('readyok')

        elif smove == 'ucinewgame':
            stack.append('position fen ' + tools.FEN_INITIAL)

        # syntax specified in UCI
        # position [fen  | startpos ]  moves  ....
        
        elif smove.startswith('setoption'):
            params = smove.split(' ')
            idx = smove.find('name')
            if idx >= 0:
                spltd = smove[idx:].split()
                opt = spltd[1]
            else:
                opt = None
            if opt != None and spltd[2] == "value" and opt in options_org:
                try:
                    spltd[3] = int(spltd[3])
                except ValueError:
                    try:
                        spltd[3] = float(spltd[3])
                    except:
                        pass
                if opt == "EvalRoughness" and type(spltd[3]) != str:
                    sunfish.EVAL_ROUGHNESS = spltd[3]
            
        elif smove.startswith('position'):
            params = smove.split(' ')
            idx = smove.find('moves')

            if idx >= 0:
                moveslist = smove[idx:].split()[1:]
            else:
                moveslist = []

            if params[1] == 'fen':
                if idx >= 0:
                    fenpart = smove[:idx]
                else:
                    fenpart = smove

                _, _, fen = fenpart.split(' ', 2)

            elif params[1] == 'startpos':
                fen = tools.FEN_INITIAL

            else:
                pass
            
            pos = tools.parseFEN(fen)
            color = WHITE if fen.split()[1] == 'w' else BLACK

            for move in moveslist:
                pos = pos.move(tools.mparse(color, move))
                nhist.append(pos.board)
                color = 1 - color

        elif smove.startswith('go'):
            #  default options
            depth = 1000
            movetime = -1

            _, *params = smove.split(' ')
            for param, val in zip(*2*(iter(params),)):
                if param == 'depth':
                    depth = int(val)
                if param == 'movetime':
                    movetime = int(val)
                if param == 'wtime':
                    our_time = int(val)
                if param == 'btime':
                    opp_time = int(val)

            moves_remain = 40

            start = time.time()
            ponder = None
            for sdepth, _move, _score in searcher.search(pos, nhist):
                moves = tools.pv(searcher, pos, include_scores=False)

                if show_thinking:
                    entry = searcher.tp_score.get((pos, sdepth, True))
                    score = int(round((entry.lower + entry.upper)/2))
                    usedtime = int((time.time() - start) * 1000)
                    output('info depth {} score cp {} time {} nodes {} pv {}'.format(sdepth, score, usedtime, searcher.nodes, moves))

                if len(moves) > 5:
                    ponder = moves[1]

                if movetime > 0 and (time.time() - start) * 1000 > movetime:
                    break

                if (time.time() - start) * 1000 > our_time/moves_remain:
                    break

                if sdepth >= depth:
                    break

            entry = searcher.tp_score.get((pos, sdepth, True))
            m, s = searcher.tp_move.get(pos), entry.lower
        
            moves = moves.split(' ')
            if len(moves) > 1:
                output(f'bestmove {moves[0]} ponder {moves[1]}')
            else:
                output('bestmove ' + moves[0])

        elif smove.startswith('time'):
            our_time = int(smove.split()[1])

        elif smove.startswith('otim'):
            opp_time = int(smove.split()[1])

        else:
            pass

if __name__ == '__main__':
    main()

