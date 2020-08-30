var DNFServerSelect = {};

DNFServerSelect.STD_DATA =
    [

        {
            t: "广东", v: "21", opt_data_array: [

                {t: "广东一区", v: "1", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东二区", v: "15", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东三区", v: "22", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东四区", v: "45", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东五区", v: "52", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东六区", v: "65", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东七区", v: "71", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东八区", v: "81", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东九区", v: "89", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东十区", v: "98", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东十一区", v: "105", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东十二区", v: "126", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广东十三区", v: "134", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "福建", v: "33", opt_data_array: [

                {t: "福建一区", v: "14", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "福建二区", v: "44", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "福建3/4区", v: "80", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "浙江", v: "30", opt_data_array: [

                {t: "浙江一区", v: "11", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "浙江二区", v: "21", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "浙江三区", v: "55", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "浙江4/5区", v: "84", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "浙江六区", v: "116", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "浙江七区", v: "129", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "北京", v: "22", opt_data_array: [

                {t: "北京一区", v: "2", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "北京2/4区", v: "35", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "北京三区", v: "72", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "上海", v: "23", opt_data_array: [

                {t: "上海一区", v: "3", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "上海二区", v: "16", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "上海三区", v: "36", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "上海4/5区", v: "93", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "四川", v: "24", opt_data_array: [

                {t: "四川一区", v: "4", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "四川二区", v: "26", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "四川三区", v: "56", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "四川四区", v: "70", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "四川五区", v: "82", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "四川六区", v: "107", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "湖南", v: "25", opt_data_array: [

                {t: "湖南一区", v: "5", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖南二区", v: "25", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖南三区", v: "50", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖南四区", v: "66", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖南五区", v: "74", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖南六区", v: "85", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖南七区", v: "117", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "山东", v: "26", opt_data_array: [

                {t: "山东一区", v: "6", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "山东2/7区", v: "37", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "山东三区", v: "59", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "山东四区", v: "75", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "山东五区", v: "78", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "山东六区", v: "106", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "江苏", v: "27", opt_data_array: [

                {t: "江苏一区", v: "7", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江苏二区", v: "20", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江苏三区", v: "41", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江苏四区", v: "53", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江苏5/7区", v: "79", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江苏六区", v: "90", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江苏八区", v: "109", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "湖北", v: "28", opt_data_array: [

                {t: "湖北一区", v: "9", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北二区", v: "24", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北三区", v: "48", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北四区", v: "68", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北五区", v: "76", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北六区", v: "94", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北七区", v: "115", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "湖北八区", v: "127", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "华北", v: "29", opt_data_array: [

                {t: "华北一区", v: "10", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "华北二区", v: "19", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "华北三区", v: "54", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "华北四区", v: "87", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "西北", v: "31", opt_data_array: [

                {t: "西北一区", v: "12", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "西北2/3区", v: "46", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "东北", v: "32", opt_data_array: [

                {t: "东北一区", v: "13", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "东北二区", v: "18", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "东北3/7区", v: "23", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "东北4/5/6区", v: "83", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "西南", v: "34", opt_data_array: [

                {t: "西南一区", v: "17", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "西南二区", v: "49", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "西南三区", v: "92", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "河南", v: "35", opt_data_array: [

                {t: "河南一区", v: "27", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河南二区", v: "43", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河南三区", v: "57", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河南四区", v: "69", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河南五区", v: "77", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河南六区", v: "103", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河南七区", v: "135", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "广西", v: "36", opt_data_array: [

                {t: "广西一区", v: "28", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广西2/4区", v: "64", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广西三区", v: "88", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "广西五区", v: "133", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "江西", v: "37", opt_data_array: [

                {t: "江西一区", v: "29", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江西二区", v: "62", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "江西三区", v: "96", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "安徽", v: "38", opt_data_array: [

                {t: "安徽一区", v: "30", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "安徽二区", v: "58", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "安徽三区", v: "104", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "辽宁", v: "39", opt_data_array: [

                {t: "辽宁一区", v: "31", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "辽宁二区", v: "47", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "辽宁三区", v: "61", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "山西", v: "40", opt_data_array: [

                {t: "山西一区", v: "32", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "山西二区", v: "95", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "陕西", v: "41", opt_data_array: [

                {t: "陕西一区", v: "33", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "陕西2/3区", v: "63", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "广州", v: "42", opt_data_array: [

                {t: "广州1/2区", v: "34", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "河北", v: "43", opt_data_array: [

                {t: "河北一区", v: "38", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河北2/3区", v: "67", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河北四区", v: "118", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "河北五区", v: "132", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "重庆", v: "44", opt_data_array: [

                {t: "重庆一区", v: "39", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "重庆二区", v: "73", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "黑龙江", v: "45", opt_data_array: [

                {t: "黑龙江一区", v: "40", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "黑龙江2/3区", v: "51", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "吉林", v: "46", opt_data_array: [

                {t: "吉林1/2区", v: "42", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "云贵", v: "277", opt_data_array: [

                {t: "云南一区", v: "120", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "贵州一区", v: "122", status: "1", display: "1", opt_data_array: []}
                ,
                {t: "云贵一区", v: "124", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "天津", v: "278", opt_data_array: [

                {t: "天津一区", v: "121", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "新疆", v: "281", opt_data_array: [

                {t: "新疆一区", v: "123", status: "1", display: "1", opt_data_array: []}

            ]
        }
        ,
        {
            t: "内蒙", v: "538", opt_data_array: [

                {t: "内蒙古一区", v: "125", status: "1", display: "1", opt_data_array: []}

            ]
        }

    ];
