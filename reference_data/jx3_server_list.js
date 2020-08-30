var JX3ServerSelect={};

JX3ServerSelect.STD_DATA=
[

    {t:"如梦令",v:"10001",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"如梦令",v:"10001",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"白帝城",v:"10002",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"白帝城",v:"10002",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"扬州城",v:"10003",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"扬州城",v:"10003",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"秦王殿",v:"10004",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"秦王殿",v:"10004",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"忆盈楼",v:"10005",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"忆盈楼",v:"10005",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"念奴娇",v:"10006",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"念奴娇",v:"10006",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"梦江南",v:"20001",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"梦江南",v:"20001",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"破阵子",v:"20002",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"破阵子",v:"20002",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"蝶恋花",v:"20003",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"蝶恋花",v:"20003",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"长安城",v:"20004",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"长安城",v:"20004",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"幽月轮",v:"20005",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"幽月轮",v:"20005",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"荻花宫",v:"20006",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"荻花宫",v:"20006",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"四海波静",v:"30001",status:"1", s:"0", c:"5", sk:"ios", ck:""}
,
    {t:"唯我独尊",v:"10007",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"唯我独尊",v:"10007",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"斗转星移",v:"10008",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"斗转星移",v:"10008",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"论剑峰",v:"10009",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"论剑峰",v:"10009",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"问道坡",v:"10010",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"问道坡",v:"10010",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"三星望月",v:"10011",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"三星望月",v:"10011",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"侠客行",v:"10012",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"侠客行",v:"10012",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"落雁峰",v:"10013",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"落雁峰",v:"10013",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"战魂劫",v:"10014",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"战魂劫",v:"10014",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"洛阳城",v:"10015",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"洛阳城",v:"10015",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"三才阵",v:"10016",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"三才阵",v:"10016",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"落星湖",v:"10017",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"落星湖",v:"10017",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"仙迹岩",v:"10018",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"仙迹岩",v:"10018",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"战江湖",v:"10019",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"战江湖",v:"10019",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"烛龙殿",v:"10020",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"烛龙殿",v:"10020",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"镇山河",v:"10021",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"镇山河",v:"10021",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"狮子吼",v:"10022",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"狮子吼",v:"10022",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"春泥护花",v:"10023",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"春泥护花",v:"10023",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"华山论剑",v:"10024",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"华山论剑",v:"10024",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"折叶笼花",v:"10025",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"折叶笼花",v:"10025",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"国色天香",v:"10026",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"国色天香",v:"10026",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"情深似海",v:"10027",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"情深似海",v:"10027",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"平步青云",v:"10028",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"平步青云",v:"10028",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"飞鸢泛月",v:"10029",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"飞鸢泛月",v:"10029",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"叱咤风云",v:"10030",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"叱咤风云",v:"10030",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"倾国倾城",v:"10031",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"倾国倾城",v:"10031",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"步月登云",v:"10032",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"步月登云",v:"10032",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"大美江湖",v:"10033",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"大美江湖",v:"10033",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"比翼双飞",v:"10034",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"比翼双飞",v:"10034",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"策马江湖",v:"10035",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"策马江湖",v:"10035",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"义薄云天",v:"10036",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"义薄云天",v:"10036",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"肝胆相照",v:"10037",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"肝胆相照",v:"10037",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"笑傲江湖",v:"10038",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"笑傲江湖",v:"10038",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"梦回大唐",v:"10039",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"梦回大唐",v:"10039",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"壮志凌云",v:"10040",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"壮志凌云",v:"10040",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"侠骨柔情",v:"10041",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"侠骨柔情",v:"10041",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"名动江湖",v:"10042",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"名动江湖",v:"10042",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"龙门荒漠",v:"10043",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"龙门荒漠",v:"10043",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"枫泾古镇",v:"10044",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"枫泾古镇",v:"10044",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"英雄结义",v:"10045",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"英雄结义",v:"10045",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"萍踪侠影",v:"10046",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"萍踪侠影",v:"10046",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"快意恩仇",v:"10047",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"快意恩仇",v:"10047",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"攻无不克",v:"10048",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"攻无不克",v:"10048",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"气吞山河",v:"10049",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"气吞山河",v:"10049",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"金戈铁马",v:"10050",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"金戈铁马",v:"10050",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"七秀内坊",v:"10051",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"七秀内坊",v:"10051",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"灵霄峡",v:"10052",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"灵霄峡",v:"10052",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"永遇乐",v:"10053",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"永遇乐",v:"10053",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"夕照雷峰",v:"10054",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"夕照雷峰",v:"10054",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"八荒归元",v:"10055",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"八荒归元",v:"10055",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"乱洒青荷",v:"10056",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"乱洒青荷",v:"10056",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"乾坤一掷",v:"20007",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"乾坤一掷",v:"20007",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"风雨同舟",v:"20008",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"风雨同舟",v:"20008",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"晴昼海",v:"20009",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"晴昼海",v:"20009",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"稻香村",v:"20010",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"稻香村",v:"20010",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"夜幕星河",v:"20011",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"夜幕星河",v:"20011",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"满江红",v:"20012",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"满江红",v:"20012",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"凌烟阁",v:"20013",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"凌烟阁",v:"20013",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"南屏山",v:"20014",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"南屏山",v:"20014",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"枫华谷",v:"20015",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"枫华谷",v:"20015",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"无盐岛",v:"20016",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"无盐岛",v:"20016",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"金水镇",v:"20017",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"金水镇",v:"20017",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"藏经阁",v:"20018",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"藏经阁",v:"20018",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"饮马川",v:"20019",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"饮马川",v:"20019",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"大明宫",v:"20020",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"大明宫",v:"20020",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"生太极",v:"20021",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"生太极",v:"20021",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"战八方",v:"20022",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"战八方",v:"20022",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"离经易道",v:"20023",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"离经易道",v:"20023",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"太极广场",v:"20024",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"太极广场",v:"20024",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"听风吹雪",v:"20025",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"听风吹雪",v:"20025",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"红尘寻梦",v:"20026",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"红尘寻梦",v:"20026",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"龙争虎斗",v:"20027",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"龙争虎斗",v:"20027",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"绝代天骄",v:"20028",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"绝代天骄",v:"20028",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"战无不胜",v:"20029",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"战无不胜",v:"20029",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"金榜题名",v:"20030",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"金榜题名",v:"20030",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"双剑合璧",v:"20031",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"双剑合璧",v:"20031",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"金蛇漫舞",v:"20032",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"金蛇漫舞",v:"20032",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"海誓山盟",v:"20033",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"海誓山盟",v:"20033",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"天长地久",v:"20034",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"天长地久",v:"20034",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"独步天下",v:"20035",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"独步天下",v:"20035",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"卧虎藏龙",v:"20036",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"卧虎藏龙",v:"20036",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"名扬四海",v:"20037",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"名扬四海",v:"20037",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"纵横江湖",v:"20038",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"纵横江湖",v:"20038",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"君子如风",v:"20039",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"君子如风",v:"20039",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"侠肝义胆",v:"20040",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"侠肝义胆",v:"20040",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"缘定三生",v:"20041",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"缘定三生",v:"20041",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"日轮山城",v:"20042",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"日轮山城",v:"20042",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"铁血丹心",v:"20043",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"铁血丹心",v:"20043",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"龙飞凤舞",v:"20044",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"龙飞凤舞",v:"20044",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"无悔江湖",v:"20045",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"无悔江湖",v:"20045",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"乱世争锋",v:"20046",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"乱世争锋",v:"20046",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"风花雪月",v:"20047",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"风花雪月",v:"20047",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"一苇渡江",v:"20048",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"一苇渡江",v:"20048",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"大雄宝殿",v:"20049",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"大雄宝殿",v:"20049",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"千古风流",v:"20050",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"千古风流",v:"20050",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"九隐峰",v:"20051",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"九隐峰",v:"20051",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"绝情谷",v:"20052",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"绝情谷",v:"20052",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"思过崖",v:"20053",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"思过崖",v:"20053",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"云飞玉皇",v:"20054",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"云飞玉皇",v:"20054",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"两仪化形",v:"20055",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"两仪化形",v:"20055",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"水榭花盈",v:"10057",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"不动明王",v:"10058",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"破坚阵",v:"10059",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"风来吴山",v:"10060",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"霞流宝石",v:"10061",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"风吹荷",v:"10062",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"峰插云景",v:"10063",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"鹤归孤山",v:"10064",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"三环套月",v:"10065",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"剑冲阴阳",v:"10066",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"无我无剑",v:"10067",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"雪封冰天",v:"10068",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"霜月风华",v:"10069",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"飞燕穿林",v:"10070",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"洞天福地",v:"10071",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"四象轮回",v:"10072",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"气魄九宫",v:"10073",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"天音净气",v:"10074",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"撼岳囚虎",v:"10075",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"万夫莫敌",v:"10076",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"龙啸泽渊",v:"10077",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"傲雪惊鸿",v:"10078",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"百步穿杨",v:"10079",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"长虹贯日",v:"10080",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"烽火连城",v:"10081",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"云风扬尘",v:"10082",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"地载天岩",v:"10083",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"真火冲融",v:"10084",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"尘风飞扬",v:"10085",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"万宗归朝",v:"10086",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"大日如来",v:"10087",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"无音天罚",v:"10088",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"钵音传世",v:"10089",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"秋花隐叶",v:"10090",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"梵音狮吼",v:"10091",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"罗汉入世",v:"10092",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"伏虎劫沙",v:"10093",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"摘星换斗",v:"10094",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"破釜沉舟",v:"10095",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"叶舞倾心",v:"10096",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"羽影楼城",v:"10097",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"不系雕鞍",v:"10098",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"千瞬流云",v:"10099",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"叶落凌空",v:"10100",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"踏碎凌霄",v:"10101",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"天地焚海",v:"10102",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"瑶月烟华",v:"10103",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"太月三草",v:"10104",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"素月汐潮",v:"10105",status:"1", s:"1", c:"1", sk:"android", ck:"weixin"}
,
    {t:"水榭花盈",v:"10057",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"不动明王",v:"10058",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"破坚阵",v:"10059",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"风来吴山",v:"10060",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"霞流宝石",v:"10061",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"风吹荷",v:"10062",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"峰插云景",v:"10063",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"鹤归孤山",v:"10064",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"三环套月",v:"10065",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"剑冲阴阳",v:"10066",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"无我无剑",v:"10067",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"雪封冰天",v:"10068",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"霜月风华",v:"10069",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"飞燕穿林",v:"10070",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"洞天福地",v:"10071",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"四象轮回",v:"10072",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"气魄九宫",v:"10073",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"天音净气",v:"10074",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"撼岳囚虎",v:"10075",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"万夫莫敌",v:"10076",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"龙啸泽渊",v:"10077",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"傲雪惊鸿",v:"10078",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"百步穿杨",v:"10079",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"长虹贯日",v:"10080",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"烽火连城",v:"10081",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"云风扬尘",v:"10082",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"地载天岩",v:"10083",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"真火冲融",v:"10084",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"尘风飞扬",v:"10085",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"万宗归朝",v:"10086",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"大日如来",v:"10087",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"无音天罚",v:"10088",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"钵音传世",v:"10089",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"秋花隐叶",v:"10090",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"梵音狮吼",v:"10091",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"罗汉入世",v:"10092",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"伏虎劫沙",v:"10093",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"摘星换斗",v:"10094",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"破釜沉舟",v:"10095",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"叶舞倾心",v:"10096",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"羽影楼城",v:"10097",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"不系雕鞍",v:"10098",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"千瞬流云",v:"10099",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"叶落凌空",v:"10100",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"踏碎凌霄",v:"10101",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"天地焚海",v:"10102",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"瑶月烟华",v:"10103",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"太月三草",v:"10104",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"素月汐潮",v:"10105",status:"1", s:"0", c:"1", sk:"ios", ck:"weixin"}
,
    {t:"兰摧玉折",v:"20056",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"剑破虚空",v:"20057",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"韦陀献杵",v:"20058",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"断魂刺",v:"20059",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"九溪弥烟",v:"20060",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"平湖断月",v:"20061",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"梅隐香",v:"20062",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"梦泉虎跑",v:"20063",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"玉泉鱼跃",v:"20064",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"御风剑来",v:"20065",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"道冲无极",v:"20066",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"三清破镜",v:"20067",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"五方行尽",v:"20068",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"九转归一",v:"20069",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"万剑归宗",v:"20070",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"大道无形",v:"20071",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"万世不竭",v:"20072",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"六合独尊",v:"20073",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"鸿蒙初开",v:"20074",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"破碎星辰",v:"20075",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"傲骨迎风",v:"20076",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"天地无极",v:"20077",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"荡剑乘风",v:"20078",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"苍松挂剑",v:"20079",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"烟云破月",v:"20080",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"凌云飞霜",v:"20081",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"暮雪天寒",v:"20082",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"龙虎诛邪",v:"20083",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"凭虚御风",v:"20084",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"大道无术",v:"20085",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"惊鸿一痕",v:"20086",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"穿花回雾",v:"20087",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"狂蜂乱蝶",v:"20088",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"蝶乱七生",v:"20089",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"翩若惊鸿",v:"20090",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"三蝶戏水",v:"20091",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"江海凝光",v:"20092",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"剑神无我",v:"20093",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"剑气长江",v:"20094",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"回风舞雪",v:"20095",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"矫若游龙",v:"20096",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"上元点鬟",v:"20097",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"翔鸾舞柳",v:"20098",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"王母挥袂",v:"20099",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"曲动紫皇",v:"20100",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"五音乱心",v:"20101",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"神女未察",v:"20102",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"轻云蔽月",v:"20103",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"流风回雪",v:"20104",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"魂牵梦萦",v:"20105",status:"1", s:"1", c:"2", sk:"android", ck:"qq"}
,
    {t:"兰摧玉折",v:"20056",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"剑破虚空",v:"20057",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"韦陀献杵",v:"20058",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"断魂刺",v:"20059",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"九溪弥烟",v:"20060",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"平湖断月",v:"20061",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"梅隐香",v:"20062",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"梦泉虎跑",v:"20063",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"玉泉鱼跃",v:"20064",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"御风剑来",v:"20065",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"道冲无极",v:"20066",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"三清破镜",v:"20067",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"五方行尽",v:"20068",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"九转归一",v:"20069",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"万剑归宗",v:"20070",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"大道无形",v:"20071",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"万世不竭",v:"20072",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"六合独尊",v:"20073",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"鸿蒙初开",v:"20074",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"破碎星辰",v:"20075",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"傲骨迎风",v:"20076",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"天地无极",v:"20077",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"荡剑乘风",v:"20078",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"苍松挂剑",v:"20079",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"烟云破月",v:"20080",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"凌云飞霜",v:"20081",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"暮雪天寒",v:"20082",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"龙虎诛邪",v:"20083",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"凭虚御风",v:"20084",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"大道无术",v:"20085",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"惊鸿一痕",v:"20086",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"穿花回雾",v:"20087",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"狂蜂乱蝶",v:"20088",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"蝶乱七生",v:"20089",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"翩若惊鸿",v:"20090",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"三蝶戏水",v:"20091",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"江海凝光",v:"20092",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"剑神无我",v:"20093",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"剑气长江",v:"20094",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"回风舞雪",v:"20095",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"矫若游龙",v:"20096",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"上元点鬟",v:"20097",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"翔鸾舞柳",v:"20098",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"王母挥袂",v:"20099",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"曲动紫皇",v:"20100",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"五音乱心",v:"20101",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"神女未察",v:"20102",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"轻云蔽月",v:"20103",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"流风回雪",v:"20104",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}
,
    {t:"魂牵梦萦",v:"20105",status:"1", s:"0", c:"2", sk:"ios", ck:"qq"}

];

JX3ServerSelect.STD_SYSTEM_DATA=
[

    {t:"苹果(iOS)", v:"0", k:"ios", status:"1"}
,
    {t:"安卓(android)", v:"1", k:"android", status:"1"}

];

JX3ServerSelect.STD_CHANNEL_DATA=
[

    {t:"微信", v:"1", sk:"", k:"weixin", status:"1"}
,
    {t:"手Q", v:"2", sk:"", k:"qq", status:"1"}
,
    {t:"游客", v:"5", sk:"", k:"", status:"1"}

];
