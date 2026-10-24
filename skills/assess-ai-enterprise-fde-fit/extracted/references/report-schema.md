# 报告JSON结构

## 必填顶层字段

```json
{
  "person_name": "用户明确提供的姓名或称呼，例如张明、小雨老师（必填）",
  "generated_at": "2026-08-18",
  "summary": "不超过120字的结论",
  "scores": {
    "ai_service": 78,
    "fde": 66,
    "commercial": 52,
    "confidence": 71
  },
  "diagnosis": {
    "current_stage": "当前所处阶段",
    "recommended_route": "建议优先路线",
    "analysis": "300–500字综合诊断",
    "why": ["依据1", "依据2", "依据3"],
    "not_now": ["现在不建议做的事及原因"]
  },
  "score_analysis": {
    "ai_service": {"title": "AI企服解读", "analysis": "120–250字", "evidence": ["依据"], "next_level": "进入下一档需要什么"},
    "fde": {"title": "FDE解读", "analysis": "120–250字", "evidence": ["依据"], "next_level": "进入下一档需要什么"},
    "commercial": {"title": "商业化解读", "analysis": "120–250字", "evidence": ["依据"], "next_level": "进入下一档需要什么"}
  },
  "dimensions": {
    "ai_service": [{"name": "AI交付", "score": 80}],
    "fde": [{"name": "技术集成", "score": 72}]
  },
  "route_comparison": [
    {"route": "AI企业服务", "fit": "较适合", "why": "具体原因", "entry": "建议进入方式", "avoid": "暂时不要做什么"},
    {"route": "FDE", "fit": "条件适合", "why": "具体原因", "entry": "建议进入方式", "avoid": "暂时不要做什么"}
  ],
  "strengths": [{"title": "能力名", "detail": "证据与价值", "evidence": "E3"}],
  "capability_analysis": [
    {"name": "能力名", "level": "可包装后销售", "meaning": "这项能力是什么", "customer_value": "客户为什么愿意付费", "evidence": "已有证据", "shortfall": "当前短板", "next_proof": "下一份应补的成果"}
  ],
  "gaps": [{"title": "风险名", "detail": "影响", "action": "补强动作"}],
  "customer_matches": [{"name": "具体客群", "score": 82, "decision_maker": "决策人", "problem": "具体问题", "loss": "不解决造成的损失", "why_fit": "为什么与用户匹配", "service": "适合服务", "entry": "第一步如何切入"}],
  "primary_customer": {"profile": "具体画像", "reasons": ["理由"], "defer": "暂缓客群及原因"},
  "offer": {"name": "产品名称", "value": "一句话价值", "why_this": "为什么此刻最适合卖它", "deliverables": ["交付物"], "process": ["交付步骤"], "client_inputs": ["客户配合"], "exclusions": ["不包含"], "duration": "周期", "price": "测试价格假设", "pricing_logic": "报价依据", "acceptance": ["验收标准"], "upgrade": "升级产品"},
  "channels": {"primary": "主要渠道", "secondary": "辅助渠道", "avoid": "暂不使用渠道", "reason": "依据"},
  "four_week_plan": [{"week": "第1周", "actions": ["动作"], "targets": "量化目标"}],
  "ninety_day_plan": [{"phase": "1–30天", "goal": "目标", "actions": ["动作"]}],
  "learning_plan": [{"topic": "需要补的能力", "why": "为什么影响业务", "practice": "真实业务练习", "proof": "验收成果"}],
  "positioning": "我帮助……",
  "final_advice": "给学员的200–350字最终建议",
  "method_note": "评分依据、缺失信息和置信度说明"
}
```

分数必须为0–100。`person_name`必须来自用户明确回答，不得使用“匿名学员、匿名用户、学员、用户、直播学员、未填写、待补充”等自动占位词；用户可以主动指定昵称。数组可以增加项目，但不要删除关键内容。标准和深度模式不能只填一句话或关键词；`diagnosis.analysis`、三段`score_analysis.*.analysis`、能力解读、学习计划和`final_advice`必须提供有教学价值的具体解释。所有输出文本必须基于已确认事实；未知处写“待验证”，不要编造。

渲染命令：

```bash
python3 scripts/render_report.py assessment.json --output report.html
```
