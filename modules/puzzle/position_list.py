import chess
import chess.uci
import logging
import os
from modules.bcolors.bcolors import bcolors
from modules.puzzle.analysed import analysed
from operator import methodcaller

class position_list:
    def __init__(self, position, engine, info_handler, player_turn=True, best_move=None, evaluation=None):
        self.position = position.copy()
        self.engine = engine
        self.info_handler = info_handler
        self.player_turn = player_turn
        self.best_move = best_move
        self.evaluation = evaluation
        self.next_position = None
        self.analysed_legals = []

    def move_list(self):
        if self.next_position is None or self.next_position.ambiguous() or self.next_position.position.is_game_over():
            if self.best_move is not None:
                return [self.best_move.bestmove.uci()]
            else:
                return []
        else:
            return [self.best_move.bestmove.uci()] + self.next_position.move_list()

    def category(self):
        if self.next_position is None:
            if self.position.is_game_over():
                return 'Mate'
            else:
                return 'Material'
        else:
            return self.next_position.category()

    def generate(self):
        logging.debug(bcolors.WARNING + str(self.position) + bcolors.ENDC)
        logging.debug(bcolors.OKBLUE + 'Material Value: ' + str(self.material_difference()) + bcolors.ENDC)
        has_best = self.evaluate_best()
        if self.player_turn:
            self.evaluate_legals()
        if has_best and not self.ambiguous() and not self.game_over():
            logging.debug(bcolors.OKGREEN + "Going Deeper:")
            logging.debug("   Ambiguous: " + str(self.ambiguous()))
            logging.debug("   Game Over: " + str(self.game_over()))
            logging.debug("   Has Best Move: " + str(has_best) + bcolors.ENDC)
            self.next_position.generate()
        else:
            logging.debug(bcolors.WARNING + "Not Going Deeper:")
            logging.debug("   Ambiguous: " + str(self.ambiguous()))
            logging.debug("   Game Over: " + str(self.game_over()))
            logging.debug("   Has Best Move: " + str(has_best) + bcolors.ENDC)

    def evaluate_best(self, nodes=6000000):
        logging.debug(bcolors.OKGREEN + "Evaluating Best Move...")
        self.engine.position(self.position)
        self.best_move = self.engine.go(nodes=nodes)
        if self.best_move.bestmove is not None:
            self.evaluation = self.info_handler.info["score"][1]
            self.next_position = position_list(self.position.copy(),
                self.engine,
                self.info_handler,
                not self.player_turn)
            self.next_position.position.push(self.best_move.bestmove)
            logging.debug("Best Move: " + self.best_move.bestmove.uci() + bcolors.ENDC)
            logging.debug(bcolors.OKBLUE + "   CP: " + str(self.evaluation.cp))
            logging.debug("   Mate: " + str(self.evaluation.mate) + bcolors.ENDC)
            return True
        else:
            logging.debug(bcolors.FAIL + "No best move!" + bcolors.ENDC)
            return False

    def evaluate_legals(self, nodes=6000000):
        logging.debug(bcolors.OKGREEN + "Evaluating Legal Moves..." + bcolors.ENDC)
        for i in self.position.legal_moves:
            position_copy = self.position.copy()
            position_copy.push(i)
            self.engine.position(position_copy)
            self.engine.go(nodes=nodes)
            self.analysed_legals.append(analysed(i, self.info_handler.info["score"][1]))
        self.analysed_legals = sorted(self.analysed_legals, key=methodcaller('sort_val'))
        for i in self.analysed_legals[:3]:
            logging.debug(bcolors.OKGREEN + "Move: " + str(i.move.uci()) + bcolors.ENDC)
            logging.debug(bcolors.OKBLUE + "   CP: " + str(i.evaluation.cp))
            logging.debug("   Mate: " + str(i.evaluation.mate))
        logging.debug("... and " + str(max(0, len(self.analysed_legals) - 3)) + " more moves" + bcolors.ENDC)

    def material_difference(self):
        return sum(v * (len(self.position.pieces(pt, True)) - len(self.position.pieces(pt, False))) for v, pt in zip([0,3,3,5.5,9], chess.PIECE_TYPES))

    def is_complete(self, category, color, first_node, first_val):
        if self.next_position is not None:
            if ((category == 'Mate' and not self.ambiguous())
                or (category == 'Material' and self.next_position.next_position is not None)):
                return self.next_position.is_complete(category, color, False, first_val)
        
        if category == 'Material':
            if color:
                if (self.material_difference() > 0.2 
                    and abs(self.material_difference() - first_val) > 0.1 
                    and first_val < 2
                    and self.evaluation.mate is None):
                    return True
                else:
                    return False
            else:
                if (self.material_difference() < -0.2 
                    and abs(self.material_difference() - first_val) > 0.1
                    and first_val > -2
                    and self.evaluation.mate is None):
                    return True
                else:
                    return False
        else:
            if self.position.is_game_over():
                return True
            else:
                return False

    def ambiguous(self):
        if len(self.analysed_legals) > 1:
            if (self.analysed_legals[0].evaluation.cp is not None
                and self.analysed_legals[1].evaluation.cp is not None):
                if (self.analysed_legals[0].evaluation.cp > -200
                    or self.analysed_legals[1].evaluation.cp < -100):
                    return True
            if (self.analysed_legals[0].evaluation.mate is not None
                and self.analysed_legals[1].evaluation.mate is not None):
                if (self.analysed_legals[0].evaluation.mate < 1
                    and self.analysed_legals[1].evaluation.mate < 1):
                    return True
            if (self.analysed_legals[0].evaluation.mate is not None
                and self.analysed_legals[1].evaluation.cp is not None):
                if (self.analysed_legals[1].evaluation.cp < -200):
                    return True
        return False

    def game_over(self):
        return self.next_position.position.is_game_over()
