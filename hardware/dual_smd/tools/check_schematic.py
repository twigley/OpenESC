#!/usr/bin/env python3
"""Independent check of kicad/dual_esc.kicad_sch: parses the S-expression,
places every symbol pin from the embedded lib_symbols, and rebuilds the
netlist from labels at pin endpoints. Fails if any pin is unlabelled, any
label floats, or the nets differ from gen_schematic.PARTS."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen_schematic as g

def parse(s):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)
    st=[[]]
    for t in tok:
        if t=='(': st.append([])
        elif t==')': x=st.pop(); st[-1].append(x)
        else: st[-1].append(t[1:-1] if t.startswith('"') else t)
    assert len(st)==1, "unbalanced parens"
    return st[0][0]

f = os.path.join(os.path.dirname(__file__), "..", "kicad", "dual_esc.kicad_sch")
root = parse(open(f).read())
find = lambda n,k: [c for c in n if isinstance(c,list) and c and c[0]==k]
libs = {}
for s in find(find(root,"lib_symbols")[0],"symbol"):
    pins={}
    for sub in find(s,"symbol"):
        for p in find(sub,"pin"):
            at=find(p,"at")[0]; num=find(p,"number")[0][1]
            pins[num]=(float(at[1]),float(at[2]))
    libs[s[1]]=pins
labels={}
for l in find(root,"label"):
    at=find(l,"at")[0]; labels.setdefault((round(float(at[1]),3),round(float(at[2]),3)),[]).append(l[1])
ncs={(round(float(find(n,"at")[0][1]),3),round(float(find(n,"at")[0][2]),3)) for n in find(root,"no_connect")}
got={}; used=set(); errs=[]
for s in find(root,"symbol"):
    lib=find(s,"lib_id")[0][1]; at=find(s,"at")[0]; X,Y=float(at[1]),float(at[2])
    ref=[p[2] for p in find(s,"property") if p[1]=="Reference"][0]
    for num,(px,py) in libs[lib].items():
        k=(round(X+px,3),round(Y-py,3))
        if k in labels:
            if len(set(labels[k]))>1: errs.append(f"{ref}.{num} has conflicting labels {labels[k]}")
            got.setdefault(labels[k][0],set()).add(f"{ref}.{num}"); used.add(k)
        elif k in ncs: got.setdefault(None,set()).add(f"{ref}.{num}"); used.add(k)
        else: errs.append(f"{ref}.{num} unconnected")
floating=set(labels)-used
if floating: errs.append(f"{len(floating)} floating labels")
want={}
for ref,sym,val,fp,pins,mpn in g.PARTS:
    for num,net in pins.items(): want.setdefault(net,set()).add(f"{ref}.{num}")
if got!=want:
    for n in set(got)|set(want):
        if got.get(n)!=want.get(n): errs.append(f"net {n}: file={sorted(got.get(n,[]))} spec={sorted(want.get(n,[]))}")
print("\n".join(errs) if errs else f"OK: {len(libs)} symbols, {sum(len(v) for v in got.values())} pins, {len([n for n in got if n])} nets match spec")
sys.exit(1 if errs else 0)
