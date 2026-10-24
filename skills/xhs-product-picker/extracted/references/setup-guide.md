# 飞书案例库配置指南

## 你为什么需要这个

本 skill 自带一份离线案例摘要，不连飞书也能用。但连上在线案例库后，你可以：
- 搜索 350+ 条真实小红书虚拟产品案例
- 获取持续更新的最新案例数据
- 用真实销量/定价数据验证选品方向

配置只需 2 步，2 分钟。

---

## 第 1 步：复制案例库到你的飞书

打开这个链接：

**https://my.feishu.cn/base/FbiAbRsyeaUTiOswW6Uc2l0TnQh?from=from_copylink**

点击右上角 **「复制到我的空间」**（或「另存为」），案例库会出现在你的飞书云空间里。

## 第 2 步：获取你的 Base Token，填入下方

打开你刚复制的 Base，浏览器地址栏里的 URL 格式是：

```
https://xxx.feishu.cn/base/XXXXXXXXXXXXX
```

`/base/` 后面的那串字符就是你的 Base Token。把它填到下面：

```yaml
# 你的飞书案例库配置
base_token: YOUR_BASE_TOKEN_HERE
table_id: tblvkzwrwK6dFzwn
```

> Table ID 复制后一般不变。如果不一样，在你复制后的 Base 里点进数据表，URL 中 `/table/` 后面的就是 table_id。

## 第 3 步：告诉 Agent 配置完成

填好 token 后，在你的 skill 里找到「数据源 → 飞书案例库」部分，把 `YOUR_BASE_TOKEN_HERE` 替换成你的真实 token。

然后对这个 skill 说一句：**「我已配置好飞书案例库」**，我就会开始用在线案例库帮你做选品验证。

---

## 可选：方法论文档

如果你有选品方法论文档的飞书 wiki 权限，同样复制后填入 wiki token 和 doc obj_token。没有就跳过，不影响使用。
