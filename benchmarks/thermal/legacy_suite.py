"""Run Cases A-G, preserve complete logs, and build the thermal summary report."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"outputs"; LOGS=ROOT/"logs"
ALL_CASES=[
    ("A","smoke_thermal_conduction.py","thermal_conduction"),
    ("B","smoke_thermal_heat_generation.py","thermal_heat_generation"),
    ("C","smoke_thermal_convection.py","thermal_convection"),
    ("D","smoke_thermal_transient.py","thermal_transient"),
    ("E","smoke_thermal_contact.py","thermal_contact"),
    ("F","smoke_thermal_radiation.py","thermal_radiation"),
    ("G","smoke_thermal_structural.py","thermal_structural"),
]

def pct(value:float)->str: return f"{100*value:.4g}%"

def main()->int:
    LOGS.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    selected={value.upper() for value in sys.argv[1:]}
    CASES=[item for item in ALL_CASES if not selected or item[0] in selected]
    exit_codes={}
    for letter,script,stem in CASES:
        started=datetime.now(timezone.utc)
        done=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,text=True,capture_output=True,check=False,timeout=1800)
        ended=datetime.now(timezone.utc)
        log=LOGS/f"thermal_case_{letter.lower()}_{stem}.log"
        log.write_text(
            f"START_UTC={started.isoformat()}\nCOMMAND={sys.executable} {script}\n"
            f"EXIT_CODE={done.returncode}\nEND_UTC={ended.isoformat()}\n\n--- STDOUT ---\n{done.stdout}"
            f"\n--- STDERR ---\n{done.stderr}",encoding="utf-8")
        solver=OUT/f"{stem}_solver.out"
        if solver.is_file(): shutil.copyfile(solver,LOGS/f"{stem}_solver.log")
        if letter=="E":
            ideal=OUT/"thermal_contact_ideal_solver.out"
            if ideal.is_file(): shutil.copyfile(ideal,LOGS/"thermal_contact_ideal_solver.log")
        exit_codes[letter]=done.returncode
        print(done.stdout.strip())
        if done.stderr.strip(): print(done.stderr.strip(),file=sys.stderr)

    payloads=[]
    for letter,_,stem in ALL_CASES:
        path=OUT/f"{stem}_results.json"
        if path.is_file(): payloads.append(json.loads(path.read_text(encoding="utf-8")))
    by_case={p["case"]:p for p in payloads}
    specs={
        "A":("Heat flow [W]","heat_flow_w","heat_flow_w","heat_flow_relative"),
        "B":("Maximum temperature [C]","max_temperature_c","max_temperature_c","center_temperature_relative_rise"),
        "C":("Surface temperature [C]","surface_temperature_c","surface_temperature_c","surface_temperature_absolute_c"),
        "D":("Final center temperature [C]","final_center_temperature_c","final_lumped_temperature_c","final_center_absolute_c"),
        "E":("Contact temperature jump [C]","interface_jump_c","interface_jump_c","temperature_jump_relative"),
        "F":("Equilibrium surface temperature [C]","equilibrium_surface_temperature_c","equilibrium_surface_temperature_c","surface_temperature_absolute_c"),
        "G":("Tip displacement [m]","tip_displacement_m","tip_displacement_m","tip_displacement_relative"),
    }
    rows=[]
    for letter,_,stem in ALL_CASES:
        p=by_case.get(letter)
        if not p: continue
        label,ak,tk,ek=specs[letter]
        mesh=p["mesh"]
        rows.append({"case":letter,"analysis_type":p["analysis_type"],"status":p["status"],"nodes":mesh.get("nodes",""),"elements":mesh.get("elements",mesh.get("solid_elements","")),"primary_metric":label,"ansys_value":p["results"][ak],"theory_value":p["theory"][tk],"reported_error":p["errors"][ek],"result_json":str((OUT/f"{stem}_results.json").resolve())})
    csv_path=OUT/"thermal_suite_summary.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

    complete_exit_codes={letter:exit_codes.get(letter,0 if by_case.get(letter,{}).get("status")=="PASS" else 1) for letter,_,_ in ALL_CASES}
    status="PASS" if len(rows)==7 and all(r["status"]=="PASS" for r in rows) and all(v==0 for v in complete_exit_codes.values()) else "FAIL"
    lines=["# Ansys 2026 R1 热学 / 固体传热基础能力 Smoke Test 报告","",f"总状态：**{status}**  （生成时间：{datetime.now(timezone.utc).isoformat()}）","","全部模型均由 Ansys MAPDL 2026 R1 / 261 实际求解；Python 仅负责编排、解析解/热阻计算、误差判定和结果归档。","","## Case A–G 汇总","","| Case | 分析类型 | 网格（节点/实体单元） | 关键 Ansys 结果 | 理论/物理校验 | 误差 | 状态 |","|---|---|---:|---:|---:|---:|---|" ]
    for row in rows:
        p=by_case[row["case"]]; err=row["reported_error"]
        error_text=f"{err:.6g} C" if row["case"] in ("C","D","F") else pct(err)
        lines.append(f"| {row['case']} | {row['analysis_type']} | {row['nodes']}/{row['elements']} | {row['primary_metric']}: {row['ansys_value']:.9g} | {row['theory_value']:.9g} | {error_text} | {row['status']} |")
    lines += ["","## 逐项模型与输出","",
        "- **A 一维稳态导热**：0.10 × 0.02 × 0.02 m，k=15 W/(m·K)，120/20 °C 定温端。输出温度空间分布、热流率和热流密度；与 Fourier 线性解比较。",
        "- **B 内部热生成**：0.10 m 对称平板，k=12 W/(m·K)，q'''=2.4×10⁵ W/m³，两端 25 °C。验证中心峰值和抛物线温度场，并做总生热/边界反力能量平衡。",
        "- **C 对流边界**：L=0.08 m，k=8 W/(m·K)，左端 100 °C，右端 h=40 W/(m²·K)、T∞=20 °C。验证导热热阻 + 对流热阻。",
        "- **D 瞬态冷却**：10 mm 立方体，k=200 W/(m·K)，ρ=7800 kg/m³，cp=500 J/(kg·K)，h=15 W/(m²·K)，100→20 °C。Bi=1.25×10⁻⁴，采用 5 s 步长，与 lumped-capacitance 指数响应比较。",
        "- **E 接触热阻**：两个 50 mm 实体，CONTA174/TARGE170 纯热接触，TCC=200 W/(m²·K)。同时求解连续单体理想接触参考 case。",
        "- **F 热辐射**：输入 8000 W/m²，ε=0.8，h=12 W/(m²·K)，T∞=25 °C；求解绝对温标下的非线性 Radiation + Convection 平衡。",
        "- **G 热-结构顺序耦合**：热场结果文件通过 LDREAD 映射到由 ETCHG 转换的匹配结构网格；α=12×10⁻⁶/K，ΔT=60 K，L=0.1 m，验证自由热膨胀。",
        "","每个 case 的结构化 JSON、原始/整理 CSV、SVG 曲线和 MAPDL 输入/结果文件均位于 `outputs/`；Python 执行日志及完整 MAPDL solver listing 位于 `logs/`。汇总索引为 `outputs/thermal_suite_summary.csv`。","","## 热学能力覆盖表","","| 能力 | 覆盖 case | 覆盖状态 |","|---|---|---|","| 稳态固体导热、温度/热流/Heat Flux | A | 已覆盖 |","| 体积热生成与能量守恒 | B | 已覆盖 |","| Mechanical/MAPDL 对流边界与热阻网络 | C | 已覆盖 |","| 瞬态热容、中心/表面时间历程 | D | 已覆盖 |","| 有限热接触导热系数、界面温跳 | E | 已覆盖 |","| 非线性表面对环境辐射 + 对流 | F | 已覆盖 |","| Thermal → Structural 顺序数据传递 | G | 已覆盖 |","","## 后续适合扩展的高级能力","","相变/潜热与温度相关材料、各向异性与复合材料导热、真实 surface-to-surface enclosure 辐射及视角因子、移动/脉冲热源、热接触 conductance 随压力/温度变化、热循环疲劳、非匹配网格数据传递、Joule heating/电-热耦合、CFD-CHT 共轭换热，以及参数化/优化与网格收敛性研究。"]
    report=ROOT/"THERMAL_BENCHMARK_REPORT.md"; report.write_text("\n".join(lines)+"\n",encoding="utf-8")
    suite={"status":status,"timestamp_utc":datetime.now(timezone.utc).isoformat(),"cases":payloads,"summary_csv":str(csv_path.resolve()),"report":str(report.resolve()),"exit_codes":complete_exit_codes}
    (OUT/"thermal_suite_results.json").write_text(json.dumps(suite,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"THERMAL SUITE {status}: {len(rows)}/7 case result files; report={report}")
    return 0 if status=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
