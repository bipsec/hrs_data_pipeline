from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Set
from src.models.ahead1993 import Ahead1993Variable, Ahead1993ValueCode, Ahead1993Section, Ahead1993Codebook,VariableLevel

# Define the source (can be a local file path or a URL)
# Need to access path variable from environment
#TODO
source = Path("C:/research_position/hrs_data_pipeline_updated/hrs_data_pipeline/data/HRS Data/1993/Core/a93core/a93cb/")


#TODO
#Cases not handled: 
# V368 not sure on meaning in codebook
# V479
import json
import re


levelMap = {
    "HH": "Household",
    "Household": "Household",
    "RESP": "Respondent",
    "Respondent": "Respondent",
    "HELP": "Helper",
    "HELPER": "Helper",
    "Helper": "Helper",
    "PERSONS": "Other Person",
    "PERSON": "Other Person",
    "Other Person": "Other Person", #may need to append this to model
    "REMOVED": "Removed",
    "Removed": "Removed" # not sure what to do with this level
    #may need to add more
}


    

def frequencyCount(lines: list[str], vname = "xxxxxx") -> int:
    #check all value codes to figure out the frequency count
    fCount = 100
    for l in lines[1:]:
        if l.strip().startswith(vname) and fCount != 100:
            break
        matchF = re.match(r'^((?:\d+\s+)+)\.*', l.strip())
        if matchF:
            f = len(matchF.group(1).split())
            if fCount > f:
                fCount = f
    return fCount

def combinedVariable(text: str, remVars: List[Ahead1993Variable], variableName: str, description: str, levels: List[str], sectionCode: str) -> List[Ahead1993Variable]:
    print("Combined" + variableName)
    variables: List[Ahead1993Variable] = []
    dashMatch = re.search(r'-{8,}(.*)', text, re.DOTALL)
    if dashMatch:
        valueCodes: List[Ahead1993ValueCode] = []
        ntext = dashMatch.group(1)
        fixlines = [l for l in ntext.splitlines() if l.strip() != ""]


        line1 = fixlines[0].strip().split() if len(fixlines) > 0 else ""
        combineVars: List[Ahead1993Variable] = []
        k = 0
        for l in fixlines:
            line = l.strip().split()
            for v in line:
                for r in remVars:
                    if r.name in v:
                        print("works")
                        remVars.remove(r)
                        combineVars.append(r)
                        break
            k += 1
            if len(combineVars) > 0:
                break
        variables.extend(remVars)
        remVars.clear()
        if len(combineVars) == 0:
            return variables


        fCount = len(combineVars) + 1 # include current variable
        i = 1 + k
        while i < len(fixlines):
            line = fixlines[i]
            if "Mean" in line or "Std Dev" in line or "Minimum" in line or "Maximum" in line:
                i += len(combineVars) + 2
                continue
            valueLine = line.strip().split(maxsplit=fCount)
            if len(valueLine) < fCount + 1:
                i += 1
                continue
            frequencies = valueLine[0:fCount]
            valueCodePart = valueLine[fCount]
            
            if "..." in valueCodePart:
                print(frequencies)
                codeMatch = re.search(r'([0-9A-Z\s]+)\.{3,}\s*([A-Z\.0-9]+)', valueCodePart)
                if codeMatch:
                    fDict = {}
                    for j, f in enumerate(frequencies[:-1]):
                        fDict[combineVars[j].name] = f
                    
                    fDict.update({variableName: frequencies[-1]})
                    valueCode = Ahead1993ValueCode(
                        code=codeMatch.group(2).strip(),
                        label=codeMatch.group(1).strip(),
                        frequency=fDict,
                        is_missing=False,
                        is_range=False
                    )
                    valueCodes.append(valueCode)
                    i += 1
                    continue
            if "INAP" in valueCodePart:
                inapMatch = re.match(r'INAP(.*)', valueCodePart.strip())
                if inapMatch:
                    fDict = {combineVars[j].name: f for j, f in enumerate(frequencies[:-1])}
                    fDict.update({variableName: frequencies[-1]})
                    valueCode = Ahead1993ValueCode(
                        code="INAP",
                        label=inapMatch.group(1).removeprefix(",").strip(),
                        frequency=fDict,
                        is_missing=False,
                        is_range=False
                    )
                    valueCodes.append(valueCode)
                    i += 1
                    break
            valueCodePart = valueCodePart.split(maxsplit=1)
            print(valueCodePart)
            code = valueCodePart[0]
            label = valueCodePart[1] if len(valueCodePart) > 1 else ""
            fDict = {combineVars[j].name: f for j, f in enumerate(frequencies[:-1])}
            fDict.update({variableName: frequencies[-1]})
            valueCode = Ahead1993ValueCode(
                code=code,
                label=label,
                frequency=fDict,
                is_missing=False,
                is_range=False
            )
            valueCodes.append(valueCode)
            i += 1
        for v in combineVars:
            newCodes: List[Ahead1993ValueCode] = [] # get codes that correspond to variable
            for vcode in valueCodes:
                print(vcode)
                vname = v.name
                ncode = Ahead1993ValueCode(
                    code=vcode.code,
                    label=vcode.label,
                    frequency={levels[0]: vcode.frequency[vname]},
                    is_missing=vcode.is_missing,
                    is_range=vcode.is_range
                )
                newCodes.append(ncode)

            variable = Ahead1993Variable(
                name=v.name,
                description=v.description,
                levels=v.levels,
                year=1993,
                section=sectionCode,
                value_codes=newCodes,
                has_value_codes=len(newCodes) > 0,
                is_skipped=False
            )
            variables.append(variable)
        #current variable
        newCodes = []
        for vcode in valueCodes:
            ncode = Ahead1993ValueCode(
                code=vcode.code,
                label=vcode.label,
                frequency={levels[0]: vcode.frequency[variableName]},
                is_missing=vcode.is_missing,
                is_range=vcode.is_range
            )
            newCodes.append(ncode)
        variable = Ahead1993Variable(
            name=variableName,
            description=description,
            levels=[levelMap[k] for k in levels],
            year=1993,
            section=sectionCode,
            value_codes=newCodes,
            has_value_codes=len(newCodes) > 0,
            is_skipped = False
        )
        variables.append(variable)
        return variables
    return variables

def rangeVariable(text: str, variableName: str, description: str, levels: List[str], sectionCode: str) -> List[Ahead1993Variable]:
    skipList = ["V368A1-A11", "V393A1-A11", "V748A1-A10", "V1151A1-A8", "V1693A1-A8"] # skipping these to prioritize speed
    variables = []
    valueCodes: List[Ahead1993ValueCode]= []
    #haven't figured out what this format in the codebook means
    variableBase = variableName.split("-")[0][:-2]
    letterNum = variableName.split("-")[1]
    letter = letterNum[0]
    num = int(letterNum[1:])
    
    RangeMap = [letter + str(k) for k in range(1, num + 1)]

    if variableName in skipList:
        for v in RangeMap:
            variable = Ahead1993Variable(
                name = variableBase + v,
                description = description,
                levels = [levelMap[k] for k in levels], #maps level short hand to actual
                year = 1993,
                section = sectionCode,
                value_codes = [],
                has_value_codes = False,
                is_skipped = True
            )
            variables.append(variable)
        return variables

    dashMatch = re.search(r'-{8,}(.*)', text, re.DOTALL)
    if dashMatch:
        text = dashMatch.group(1)

    fixText = re.sub(r'\n(?!\s*(\d|INAP|' + variableBase + r'))', ' ', text)
    fixLines = fixText.splitlines()
    if "Mean" and "Std Dev" and "Minimum" and "Maximum" in fixLines[0]:
        fixLines = fixLines[len(RangeMap):]
    fCount = frequencyCount(fixLines, variableBase)

    if "...." in text:
        i = 1 #skip name line
        while i < len(fixLines):
            
            line = fixLines[i].strip()
            
            c = 0
            if variableBase in line and len(valueCodes) > 0:
                
                baseline = line.split()
                for l in baseline:
                    if variableBase in l:
                        c+=1
                fCount = c
                i += 1
                b = 0
                line = fixLines[i].strip()
                while i < len(fixLines):
                    line = fixLines[i].strip()
                    fr = line.split(maxsplit=fCount)
                    if len(fr) < fCount + 1:
                        i += 1
                        continue
                    c = len(valueCodes[b].frequency)
                    valueCodes[b].frequency.update({str(c+j): f for j, f in enumerate(fr[0:fCount])})
                    b += 1
                    i += 1
                break

            linematch = re.match(r'^\d.*', line)
            if not linematch:
                i += 1
                continue

            inapMatch = re.match(r'(?:\d\s)*\.?\s?INAP.*', line.strip())
            if inapMatch:
                code = line.split(maxsplit=fCount)
                frequencies = code[0:fCount]
                valueCodeName = code[fCount]
                valueCode = Ahead1993ValueCode(
                    code = "INAP",
                    label = re.sub(r'\s+',' ', valueCodeName.removeprefix("INAP,")).strip(),
                    frequency = {j: f for j, f in enumerate(frequencies)},
                    is_missing = False,
                    is_range = False
                )
                valueCodes.append(valueCode)
                i += 1
                continue
            if "." not in line:
                #format is probably like 1 2 Code Description
                code = line.strip().split(maxsplit=fCount)
                if len(code) < fCount + 1:
                    i += 1
                    continue
                frequencies = code[0:fCount]
                codePart = code[fCount].split(maxsplit=1)
                code = codePart[0]
                label = codePart[1] if len(codePart) > 1 else ""
                valueCode = Ahead1993ValueCode(
                    code = code,
                    label = label,
                    frequency = {str(j): f for j, f in enumerate(frequencies)},
                    is_missing = False,
                    is_range = False
                )
                valueCodes.append(valueCode)    
                i+=1
                continue
            
            code = line.split(maxsplit=fCount)
            frequencies = code[0:fCount]
            valueCodeName = code[fCount]
            valCode = ""
            value = re.match(r'^([^\.]+)\.+\s*((?:\.D|\.R|[^\s\.][^\s]*)).*', code[fCount])
            if value:
                label = re.sub(r'\s+', ' ', value.group(1).strip())
                valCode = value.group(2)
            else:
                i += 1
                continue
            valueCode = Ahead1993ValueCode(
                code = valCode,
                label = valueCodeName.split(".", maxsplit=1)[0].strip(),
                frequency = {str(j): f for j, f in enumerate(frequencies)},
                is_missing = False,
                is_range = False
            )
            valueCodes.append(valueCode)
            i += 1
    for v in valueCodes:
        print(v.frequency)
    if len(valueCodes) == 0:
        return variables
    rangeVars = [

        Ahead1993Variable(name= variableBase + k,
            description = description,
            year = 1993,
            section = sectionCode,
            levels = [levelMap[k] for k in levels], #maps level short hand to actual
            value_codes = [
                Ahead1993ValueCode(code = v.code, 
                    label = v.label, 
                    frequency = {levelMap[levels[0]]: v.frequency[str(j)]}, #use only the variable frequency for level A2
                    is_missing = v.is_missing, 
                    is_range = v.is_range) for v in valueCodes],
            has_value_codes = len(valueCodes) > 0,
        ) for j, k in enumerate(RangeMap)
    ]
    variables.extend(rangeVars)
    return variables

def basicVariable(text: str, lines: List[str], variableName: str, description: str, levels: List[str], sectionCode: str) -> List[Ahead1993ValueCode]:
    valueCodes: List[Ahead1993ValueCode] = []
    dashMatch = re.search(r'-{8,}(.*)', text, re.DOTALL)
    if dashMatch:
        print(variableName)
        text = dashMatch.group(1)
    lev = levels
    #look for line with levels for frequency columns
    for n in lines:
        n = n.strip()
        if n.startswith("HH") or n.startswith("RESP"):
            lev = n.split()
            break

    # fix text so value codes are on a single line
    fixText = re.sub(r'\n(?!\s+(\d|INAP))', ' ', text)
    fixLines = fixText.splitlines()

    #check all value codes to figure out the frequency count
    fCount = frequencyCount(fixLines)

    if fCount != 100:
        i = 1
        #test for mean/std dev/Minimum Maximum
        if "Mean" and "Std Dev" and "Minimum" and "Maximum" in fixLines[0]:
            i = 2
        while i < len(fixLines):
            line = fixLines[i].strip()
            print(line)
            if line == "":
                i += 1
                continue 

            
            inapMatch = re.match(r'(\d*)\s*\.?\s*INAP(.*)', line.strip())
            if inapMatch:
                #assuming 0 or 1 frequency for now
                inapLabel = inapMatch.group(2).strip()
                removeExtra = re.sub(sectionCode + r'\d[\da-z]*\..*', '', inapLabel)
                valueCode = Ahead1993ValueCode(
                    code = "INAP",
                    label = re.sub(r'\s+', ' ', removeExtra).removeprefix(", ").strip(),
                    frequency = {levelMap[levels[0]]: inapMatch.group(1)},
                    is_missing =False,
                    is_range = False
                )
                valueCodes.append(valueCode)
                break
            if "[" in line and "]" in line:
                #assuming this is a range value code
                rangeMatch = re.match(r'(\d*)\s*\[([A-Za-z\s]*[\d\-]+[A-Za-z\s]*)\](.*)', line.strip())
                if rangeMatch:
                    frequencies = rangeMatch.group(1)
                    value = rangeMatch.group(2)
                    label = rangeMatch.group(3).strip()
                    valueCode = Ahead1993ValueCode(
                        code = value,
                        label = re.sub(r'\s+', ' ', label),
                        frequency = {levelMap[levels[0]]: frequencies},
                        is_missing = False,
                        is_range = True
                    )
                    valueCodes.append(valueCode)
                    i += 1
                    continue
            if "." not in line:
                #could be formated like: 4637     0   NONE
                code = line.strip().split(maxsplit=fCount)
                if len(code) <= fCount:
                    i += 1
                    continue
                frequencies = code[0:fCount]
                codePart = code[fCount].split(maxsplit=1)
                code = codePart[0]
                label = codePart[1] if len(codePart) > 1 else ""
                valueCode = Ahead1993ValueCode(
                    code = code,
                    label = label,
                    frequency = {lev[j]: frequency for j, frequency in enumerate(frequencies)},
                    is_missing = False,
                    is_range = False
                )
                valueCodes.append(valueCode)
                i += 1
                continue

            code = line.split(maxsplit=fCount)
            
            frequencies = code[0:fCount]
            valCode = ""
            value = re.match(r'^([^\.]+)\.+\s*((?:\.D|\.R|[^\s\.][^\s]*)).*', code[fCount])
            if value:
                label = re.sub(r'\s+', ' ', value.group(1).strip())
                valCode = value.group(2)
            else:
                i += 1
                continue
            valueCode = Ahead1993ValueCode(
                code = valCode,
                label = label,
                frequency = {lev[j]:frequency for j, frequency in enumerate(frequencies)},
                is_missing = False,
                is_range = False
            )
            valueCodes.append(valueCode)
            i += 1
    return valueCodes        

def rangeValueCodeVariable(text: str, variableName: str, description: str, levels: List[str], sectionCode: str) -> List[Ahead1993ValueCode]:

    valueCodes: List[Ahead1993ValueCode] = []
    #assume it must be a ranged value code variable
    # fix text so value codes are on a single line
    fixText = re.sub(r'\n(?!\s+(\d|INAP))', ' ', text)
    fixLines = fixText.splitlines()

    #check all value codes to figure out the frequency count
    fCount = frequencyCount(fixLines)
    if fCount != 100:
        i = 1
        while i < len(fixLines):
            line = fixLines[i]
            if line == "":
                i += 1
                continue 

            if "INAP" in line:
                #assuming 0 or 1 frequency for now
                
                inapMatch = re.match(r'(\d*)\s*\.?\s?INAP(.*)', line.strip())
                valueCode = Ahead1993ValueCode(
                    code="INAP",
                    label=re.sub(r'\s+', ' ', inapMatch.group(2).strip()),
                    frequency={levelMap[levels[0]]: inapMatch.group(1)},
                    is_missing=False,
                    is_range=False
                )
                valueCodes.append(valueCode)
                break

            code = line.split(maxsplit=fCount)
            
            frequencies = code[0:fCount]
            label = ""
            isRange = False
            rangeMatch = re.match(r'^\[(.*)\](.*)$', code[fCount].strip())
            if rangeMatch:
                vRange = rangeMatch.group(1).strip()
                label = rangeMatch.group(2).strip()
                isRange = True
            else:
                single = code[fCount].strip().split(maxsplit=1)
                vRange = single[0]
                invalidMatch = re.match(r'^(?![0-9]{1,7}|\.D|\.R)', vRange)
                if invalidMatch:
                    i += 1
                    continue
                label = single[1] if len(single) > 1 else ""


            valueCode = Ahead1993ValueCode(
                code=vRange,
                label=re.sub(r'\s+', ' ', label),
                frequency={levels[p]: freq for p, freq in enumerate(frequencies)},
                is_missing=False,
                is_range=isRange
            )
            valueCodes.append(valueCode)
            i += 1
    return valueCodes


def parseHTML(soup: BeautifulSoup, sectionCode:str):
    variables: List[Ahead1993Variable] = []
    variableSkipList: List[str] = [] #skipped value codes for sake of implementation time
    remVars: List[Ahead1993Variable] = [] #if var data is stored with a later variable
    for k in soup.find_all("a", attrs={"name": re.compile(r'[A-Z0-9\-]')}):
        variableName = k.attrs["name"]
        print(sectionCode + " " + variableName)
        text = k.get_text()
        subText = k.findChildren("b")
        if len(subText) > 0:
            addedText = subText[0].get_text()
            text = addedText + "\n" + k.get_text()
        lines = text.splitlines()
        description = ""
        levels = []
        splitVar = False # sometimes the variables are split into seperate html elements,
        for r in remVars:
            if r.name == variableName:
                description = r.description
                levels = r.levels
                remVars.remove(r)
                splitVar = True
                break
        
                
        if not splitVar:
        
            lines = [l.strip() for l in lines if l.strip() != ""] # remove blank lines
            
            line = lines[0] # V100 [RESP] DESCRIPTION
            levelDescriptionMatch = re.match(r'^[A-Z0-9\-\_]+\s+\[([A-Z\s\,]+)\]\s*(.*)$', line)
            if levelDescriptionMatch:
                
                levels = [k.strip() for k in levelDescriptionMatch.group(1).split(',')]
                description = levelDescriptionMatch.group(2)
                
            if len(lines) == 1:
                variable = Ahead1993Variable(
                    name=variableName,
                    description=description,
                    levels=[levelMap[k] for k in levels], #maps level short hand to actual
                    year=1993,
                    section=sectionCode,
                    value_codes=[],
                    has_value_codes=False,
                    is_skipped=False
                )
                remVars.append(variable)
                continue
        else:
            variables.extend(remVars)
            remVars = []
            lines = [l.strip() for l in lines if l.strip() != ""] # remove blank lines
            if len(lines) < 1:
                print("no Lines " + variableName)
                variable = Ahead1993Variable(
                    name=variableName,
                    description=description,
                    levels=[levelMap[k] for k in levels], #maps level short hand to actual
                    year=1993,
                    section=sectionCode,
                    value_codes=[],
                    has_value_codes=False,
                    is_skipped=False
                )
                remVars.append(variable)
                continue
        valueCodes: List[Ahead1993ValueCode] = []


        if variableName == "V1010":
            variable = Ahead1993Variable(
                name=variableName,
                description=description,
                levels=[levelMap[k] for k in levels], #maps level short hand to actual
                year=1993,
                section=sectionCode,
                value_codes=[],
                has_value_codes=False,
                is_skipped=True
            )
            variables.append(variable)
            continue

        #variable name ends in c can have format like: 100   0 = NONE skipping this for now to prioritize speed
        if variableName.endswith("C") and text.count("=") > 3:
            if len(remVars) > 0:
                for r in remVars:
                    if r.name in text:
                        r.is_skipped = True
                        variableSkipList.append(r.name)
                        variables.append(r)
                        remVars.remove(r)
                variables.extend(remVars)
                remVars = []
            variableSkipList.append(variableName)
            variable = Ahead1993Variable(
                name=variableName,
                description=description,
                levels=[levelMap[k] for k in levels], #maps level short hand to actual
                year=1993,
                section=sectionCode,
                value_codes=[],
                has_value_codes=False,
                is_skipped=True
            )
            variables.append(variable)
            continue

        #combined variable data
        if len(remVars) > 0:
            print(remVars)
            vars = combinedVariable(text, remVars, variableName, description, levels, sectionCode)
            if len(vars) > 0:
                variables.extend(vars)
                wasCombined = False
                for v in vars:
                    if v.name == variableName:
                        wasCombined = True
                        break
                if wasCombined:
                    continue


                    
        #variable range special case V100A1-A4
        if "-" in variableName:
            vars = rangeVariable(text, variableName, description, levels, sectionCode)
            if len(vars) > 0:
                print(vars)
                variables.extend(vars)
                continue
            else:
                remVars.append(Ahead1993Variable(
                    name=variableName,
                    description=description,
                    levels=[levelMap[k] for k in levels], #maps level short hand to actual
                    year=1993,
                    section=sectionCode,
                    value_codes=[],
                    has_value_codes=False,
                    is_skipped=False
                ))
            

        
        #... value code format still not every one (PN):
        if "...." in text:
            vCodes = basicVariable(text, lines, variableName, description, levels, sectionCode)
            valueCodes.extend(vCodes)
            
            

        #handle ranged value codes
        else:
            vCodes = rangeValueCodeVariable(text, variableName, description, levels, sectionCode)
            valueCodes.extend(vCodes)
        variable = Ahead1993Variable(
            name=variableName,
            description=description,
            levels=[levelMap[k] for k in levels], #maps level short hand to actual
            year=1993,
            section=sectionCode,
            value_codes=valueCodes,
            has_value_codes=len(valueCodes) > 0,
            is_identifier=variableName in ['PN', 'HHID' ], #add more
            is_skipped=False
        )
        if len(valueCodes) == 0:
            remVars.append(variable)
            continue
        variables.append(variable)
    return variables
                
                
                

                    
        

        



def main(codebooks: List[Path] = []):
    sections: List[Ahead1993Section] = []
    variables: List[Ahead1993Variable] = []
    for a in codebooks:
        if a.suffix != ".html":
            continue
        with open(a, "r") as f:
            lines = f.readlines()
            sectionCode = "Z"
            sectionName = "Default"
            for line in lines:
                sectionMatch = re.search(r'SECTION\s+(\S){1,3}\.(.*)', line.strip())
                if sectionMatch:
                    sectionCode = sectionMatch.group(1)
                    sectionName = sectionMatch.group(2).strip()
                    break

            f.seek(0)
            soup = BeautifulSoup(f.read(), 'html.parser')

            vars = parseHTML(soup, sectionCode)
            print(vars[0:3])
            levSet:Set = set()
            for v in vars:
                levSet.update(v.levels)
                
            section = Ahead1993Section(
                code=sectionCode,
                name=sectionName,
                levels=levSet,
                year=1993,
                variable_count=len(vars),
                variables=[v.name for v in vars]
            )
            sections.append(section)
            variables.extend(vars)
    levSet:Set = set()
    for s in sections:
        levSet.update(s.levels)
    codebook: Ahead1993Codebook = Ahead1993Codebook(
        source="ahead_core_codebook",
        year=1993,
        sections=sections,
        variables=variables,
        total_sections=len(sections),
        total_variables=len(variables),
        levels=levSet,
        parsed_at=datetime.now()
    )
    return codebook

       
        
        


        






if __name__ == "__main__":
    main()