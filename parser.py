#!/usr/bin/python3

# EE560 GPU ISA Assembler (derived from MIPS32)

# Author: Chang Xu (cxu925@usc.edu)

# Date:    01/10/2020

import sys, os

verbose: bool = False

instList: list = []

labelDict: dict = {}

def errorExit(msg: str, errno: int):
    print("Error: " + msg)
    exit(errno)

def vprint(msg: str):
    if verbose:
        print(msg)

def printUsage():
    print(sys.argv[0] + " <assembly file>")

InstDict = {
# R-type: (type, opcode, funct)
    "ADD":      (0, 0b000000, 0b100000),
    "SUB":      (0, 0b000000, 0b100010),
    "MULT":     (0, 0b000000, 0b011000),
    "AND":      (0, 0b000000, 0b100100),
    "OR":       (0, 0b000000, 0b100101),
    "XOR":      (0, 0b000000, 0b100110),
    "SHR":      (0, 0b000000, 0b000010),
    "SHL":      (0, 0b000000, 0b000000),
    "DIV":      (0, 0b000000, 0b011010),
# I-type: (type, opcode)
    "ADDI":     (1, 0b001000),
    "ANDI":     (1, 0b001100),
    "ORI":      (1, 0b001101),
    "XORI":     (1, 0b001110),
# LW/ST
    "LW":       (2, 0b100011),
    "LWS":      (2, 0b100111),
    "SW":       (2, 0b101011),
    "SWS":      (2, 0b101111),
# BEQ/BGT
    "BEQ":      (3, 0b000100),
    "BGT":      (3, 0b000111),
# Jump/CALL
    "J":        (4, 0b000010),
    "CALL":     (4, 0b000011),
# RET
    "RET":      (5, 0b000000)
    # TODO: JR $rs or RET?
# TODO: ALLOCATE, EXIT, and NOOP
}

def rTypeParser(raw_instruction: str)-> (bool, int):
    op, _, operands = raw_instruction.partition(' ')
    ret = InstDict[op.partition('.')[0]][2] # funct

    operands = operands.partition('$')[2]
    if not operands:
        return False, 0
    ret += int(operands[0]) << 11
    # vprint("rd: " + operands[0])

    operands = operands.partition('$')[2]
    if not operands:
        return False, 0
    ret += int(operands[0]) << 21
    # vprint("rs: " + operands[0])

    operands = operands.partition('$')[2]
    if not operands:
        return False, 0
    ret += int(operands[0]) << 16
    # vprint("rt: " + operands[0])
    return True, ret

def iTypeParser(raw_instruction: str)-> (bool, int):
    operands = raw_instruction.partition('$')[2]
    if not operands:
        return False, 0
    ret = int(operands[0]) << 16
    # vprint("rt: " + operands[0])

    operands = operands.partition('$')[2]
    if not operands:
        return False, 0
    ret += int(operands[0]) << 21
    # vprint("rs: " + operands[0])

    operands = operands.partition(',')[2]
    operands = operands.strip()
    if not operands:
        return False, 0
    ret += int(operands) & 0xFFFF
    # vprint("imme: " + operands)
    return True, ret

def lsParser(raw_instruction: str)-> (bool, int):
    operands = raw_instruction.partition('$')[2]
    if not operands:
        return False, 0
    ret = int(operands[0]) << 16
    # vprint("rt: " + operands[0])

    imme = operands.partition(',')[2].partition('(')[0]
    if not imme:
        return False, 0
    ret += int(imme) & 0xFFFF
    # vprint("imme: " + imme)

    operands = operands.partition('$')[2]
    if not operands:
        return False, 0
    ret += int(operands[0]) << 21
    # vprint("rs: " + operands[0])
    return True, ret

def brParser(raw_instruction: str)-> (bool, int):
    operands = raw_instruction.partition('$')[2]
    if not operands:
        return False, 0
    ret = int(operands[0]) << 21
    # vprint("rs: " + operands[0])

    operands = operands.partition('$')[2]
    if not operands:
        return False, 0
    ret += int(operands[0]) << 16
    # vprint("rt: " + operands[0])

    operands = operands.partition(',')[2]
    operands = operands.strip()
    if operands not in labelDict:
        return False, 0
    ret += labelDict[operands] & 0xFFFF
    # vprint("Tag: " + operands)
    return True, ret

def jParser(raw_instruction: str)-> (bool, int):
    tokens = raw_instruction.split()
    if not len(tokens) == 2:
        return False, 0
    if not tokens[1] in labelDict:
        return False, 0
    ret = labelDict[tokens[1]]
    # vprint("Tag: " + tokens[1])
    return True, ret

def retParser(raw_instruction: str)-> (bool, int):
    ret = 0
    return True, ret

ParserList = [
    rTypeParser, 
    iTypeParser, 
    lsParser, 
    brParser, 
    jParser, 
    retParser
]

def parseStr(raw_instruction: str)-> int:
    vprint(raw_instruction)
    OP = raw_instruction.partition(' ')[0]
    # dotS support
    OP, dotS, _= OP.partition('.')
    if OP not in InstDict:
        errorExit("Invalid instruction: " + raw_instruction, -2)
    ind, opcode = InstDict[OP][0:2]
    ret, inst = ParserList[ind](raw_instruction)
    if not ret:
        errorExit("Invalid instruction: " + raw_instruction, -2)
    inst += opcode << 26
    if dotS:
        inst += (1 << 30)
    vprint('{:032b}'.format(inst))
    return inst

def processArgs():
    global instList, labelDict
    instList.clear()
    labelDict.clear()

    if len(sys.argv) < 2:
        printUsage()
        errorExit("ASM file not specified",-1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        errorExit(filename + " is not a valid file!", -1)

    with open(filename, "r") as fileobj:
        for line in fileobj.read().splitlines():
            head = line.partition(';')[0]
            head = head.strip()
            if not head:
                continue
            if ':' not in head:
                instList.append(head)
            else:
                label, _, inst = head.partition(':')
                assert label and (label not in labelDict) and "Duplicate Labels!"
                labelDict[label] = len(instList)
                inst = inst.strip()
                if inst:
                    instList.append(inst)

    vprint("\n------------ Recognized Instructions: ------------\n")
    for inst in instList:
        vprint(inst)

    vprint("\n--------------- Recognized Labels: ---------------\n")
    for key,value in labelDict.items():
        vprint(key + ": " + instList[value])

    # parsing
    vprint("\n-------------- Parsing Instructions --------------\n")
    for inst in instList:
        parseStr(inst)

def main():
    global verbose
    verbose = True
    processArgs()

if __name__ == "__main__":
    main()