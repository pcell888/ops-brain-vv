/*
 Navicat Premium Data Transfer

 Source Server         : 超链 2测试环境
 Source Server Type    : MySQL
 Source Server Version : 80045
 Source Host           : 192.168.1.249:3306
 Source Schema         : wlwq-enterprise-service

 Target Server Type    : MySQL
 Target Server Version : 80045
 File Encoding         : 65001

 Date: 04/03/2026 14:54:38
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for account_coupon
-- ----------------------------
DROP TABLE IF EXISTS `account_coupon`;
CREATE TABLE `account_coupon`  (
  `account_coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户优惠券ID',
  `coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '优惠券ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `coupon_source` tinyint(1) NULL DEFAULT NULL COMMENT '优惠券来源（1平台 2商家）',
  `coupon_module` tinyint(1) NULL DEFAULT 0 COMMENT '优惠券模块（1商城 2服务）',
  `coupon_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '优惠券名称',
  `coupon_type` tinyint(1) NULL DEFAULT 1 COMMENT '优惠券类型（1满减 2立减）',
  `use_scope` tinyint(1) NULL DEFAULT 0 COMMENT '使用范围（0全场通用 1分类通用 2指定店铺 3指定商品）',
  `class_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '指定分类ID',
  `class_names` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '指定分类名称',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `primary_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '指定ID',
  `primary_names` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '指定名称',
  `full_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '满值',
  `reduce_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '立减值',
  `start_time` datetime NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime NULL DEFAULT NULL COMMENT '结束时间',
  `use_status` tinyint NULL DEFAULT 0 COMMENT '使用状态（0未使用 1已使用 2已过期）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '领取时间',
  `use_time` datetime NULL DEFAULT NULL COMMENT '使用时间',
  `expire_time` datetime NULL DEFAULT NULL COMMENT '过期时间',
  `total_order_num` int NULL DEFAULT 1 COMMENT '订单数量',
  `cancel_order_num` int NULL DEFAULT 0 COMMENT '取消订单数量',
  `cross_platform_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否跨平台（0否 1是）',
  `commission_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '佣金比例(%)',
  `original_coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原优惠券ID',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '来源项目ID',
  `original_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '来源项目名称',
  `target_project_id` bigint NULL DEFAULT NULL COMMENT '目标项目ID',
  `target_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '目标项目名称',
  `original_account_coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原用户优惠券ID',
  `discount_value` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '折扣值(0-10)',
  `project_type` tinyint NULL DEFAULT 1 COMMENT '项目类型(1=商城项目,2=服务项目）',
  `project_type_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '项目类型名称',
  `original_project_logo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '来源项目logo',
  PRIMARY KEY (`account_coupon_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户优惠券表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for account_earnings_detail
-- ----------------------------
DROP TABLE IF EXISTS `account_earnings_detail`;
CREATE TABLE `account_earnings_detail`  (
  `account_earnings_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户收益明细ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '账号ID',
  `earning_status` tinyint NULL DEFAULT NULL COMMENT '收支类型（1获得 2支出）',
  `earning_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '收益名称',
  `earning_money` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '收益金额',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '公共ID（商城订单ID）',
  `earning_type` tinyint NULL DEFAULT NULL COMMENT '收益类型（1用户收益 2分销收益 3商城订单）',
  `account_type` tinyint NULL DEFAULT 1 COMMENT '账户类型（1普通用户 2服务商 3商家店铺）',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '店铺ID',
  `order_sn` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单号',
  `commission_level` int NULL DEFAULT 1 COMMENT '分销等级',
  `source` tinyint NULL DEFAULT 1 COMMENT '佣金来源（1用户 2店铺）',
  `source_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '佣金来源账号ID',
  `source_store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '佣金来源店铺ID',
  `entry_status` tinyint NULL DEFAULT 0 COMMENT '到账状态（0未到账 1已到账）',
  `expect_entry_time` datetime NULL DEFAULT NULL COMMENT '预计到账时间',
  `reality_entry_time` datetime NULL DEFAULT NULL COMMENT '实际到账时间',
  `refund_money` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '退款金额',
  PRIMARY KEY (`account_earnings_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户收益明细表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for address_book
-- ----------------------------
DROP TABLE IF EXISTS `address_book`;
CREATE TABLE `address_book`  (
  `address_book_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '地址簿ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省编码',
  `province` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市编码',
  `city` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县编码',
  `county` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '地址',
  `address_details` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '地址详情',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '纬度',
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系人',
  `contact_mobile` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系电话',
  `default_status` tinyint NULL DEFAULT 0 COMMENT '默认状态(0:不默认 1:默认)',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  PRIMARY KEY (`address_book_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '地址簿' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for age_order
-- ----------------------------
DROP TABLE IF EXISTS `age_order`;
CREATE TABLE `age_order`  (
  `age_order_id` bigint NOT NULL AUTO_INCREMENT COMMENT '年龄分段ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '名称',
  `min_num` int NULL DEFAULT NULL COMMENT '最小数量天数',
  `max_num` int NULL DEFAULT NULL COMMENT '最大数量天数',
  PRIMARY KEY (`age_order_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '年龄分段表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for agent
-- ----------------------------
DROP TABLE IF EXISTS `agent`;
CREATE TABLE `agent`  (
  `agent_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '代理商ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `agent_type` tinyint NULL DEFAULT NULL COMMENT '代理商类型（1市级代理商 2区县级代理商 3市级行业代理商 4区县级行业代理商）',
  `real_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '姓名',
  `sex` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '性别',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '手机号',
  `id_card_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证号',
  `id_card_front_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证人像面照片',
  `id_card_back_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证国徽面照片',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '所在地区',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  `total_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '总收益',
  `remaining_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '余额',
  `withdrawal_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `frozen_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '冻结金额',
  `wait_entry_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '待入账金额',
  `edit_audit_status` tinyint NULL DEFAULT -1 COMMENT '资料编辑审核状态（-1未提交 0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '资料编辑审核拒绝原因',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺分类ID',
  `city_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市ID',
  `province_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省ID',
  `county_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县ID',
  `town_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇ID',
  PRIMARY KEY (`agent_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '代理商表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for agent_apply
-- ----------------------------
DROP TABLE IF EXISTS `agent_apply`;
CREATE TABLE `agent_apply`  (
  `agent_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '代理商申请ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `agent_type` tinyint NULL DEFAULT NULL COMMENT '代理商类型（1市级代理商 2区县级代理商 3市级行业代理商 4区县级行业代理商）',
  `real_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '姓名',
  `sex` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '性别',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '手机号',
  `id_card_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证号',
  `id_card_front_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证人像面照片',
  `id_card_back_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证国徽面照片',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `audit_status` tinyint NULL DEFAULT -1 COMMENT '审核状态（-1未支付 0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '所在地区',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺分类ID',
  `city_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市ID',
  `province_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省ID',
  `county_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县ID',
  `town_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇ID',
  PRIMARY KEY (`agent_apply_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '代理商申请表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for agent_order
-- ----------------------------
DROP TABLE IF EXISTS `agent_order`;
CREATE TABLE `agent_order`  (
  `agent_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '代理商订单ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `agent_type` tinyint NULL DEFAULT NULL COMMENT '代理商类型（1市级代理商 2区县级代理商 3市级行业代理商 4区县级行业代理商）',
  `agent_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '代理商申请ID',
  `order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单号',
  `deposit_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '保证金',
  `pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付方式（APP微信 alipay_app支付宝 platform后台支付 free免费支付）',
  `pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '实付金额',
  `pay_time` datetime NULL DEFAULT NULL COMMENT '支付时间',
  `app_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'AppId',
  `trade_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付流水号',
  `pay_status` tinyint NULL DEFAULT 0 COMMENT '支付状态（0未支付 1已支付）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`agent_order_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '代理商订单' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for agent_type
-- ----------------------------
DROP TABLE IF EXISTS `agent_type`;
CREATE TABLE `agent_type`  (
  `agent_type_id` bigint NOT NULL AUTO_INCREMENT COMMENT '代理商类型ID',
  `agent_type` tinyint NULL DEFAULT NULL COMMENT '代理商类型（1市级代理商 2区县级代理商 3市级行业代理商 4区县级行业代理商）',
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '名称',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  PRIMARY KEY (`agent_type_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '代理商类型表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for api_account
-- ----------------------------
DROP TABLE IF EXISTS `api_account`;
CREATE TABLE `api_account`  (
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户id',
  `phone` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `wx_openid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信openid',
  `session_key` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '小程序授权登录返回值',
  `head_portrait` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '头像',
  `nick_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '昵称',
  `sex` tinyint NULL DEFAULT 1 COMMENT '性别（1男2女0未知）',
  `birthday` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '生日',
  `type` tinyint NULL DEFAULT 0 COMMENT '用户类型（1会员0普通用户）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未1已）',
  `last_time` datetime NULL DEFAULT NULL COMMENT '最后登录时间',
  `create_time` datetime NULL DEFAULT NULL COMMENT '注册时间',
  `parent_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '父类ID',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址',
  `brief_introduction` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '个性签名',
  `uuid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'uuid',
  `invitation_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '父类邀请码',
  `my_invitation_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '我的邀请码',
  `rong_token` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '融云token',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '密码',
  `wx_applet_openid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信小程序openid',
  `del_time` datetime NULL DEFAULT NULL COMMENT '删除时间',
  `attestation_type` tinyint NULL DEFAULT 0 COMMENT '认证类型(1:个人 2：企业 3:个体户 4:工作室)',
  `attestation_audit_status` tinyint NULL DEFAULT -1 COMMENT '审核状态（-1:未申请 0:审核中 1:审核通过 2:审核失败）',
  `last_identity_type` tinyint NULL DEFAULT 1 COMMENT '上次身份(1:用户 2:打工人)',
  `total_integral` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '累计积分',
  `residue_integral` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '剩余积分',
  `invitation_code_img` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '邀请二位码图片',
  `forbidden_status` tinyint NULL DEFAULT 0 COMMENT '禁用标识 0：否 1：是',
  `forbidden_end_time` datetime NULL DEFAULT NULL COMMENT '禁用截止时间',
  `forbidden_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '禁用原因',
  `official_accounts_open_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '公众号OpenId',
  `union_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT 'unionId',
  `official_remind_status` tinyint NULL DEFAULT 0 COMMENT '公众号提醒状态（0：无提醒 1：提醒）',
  `push_client_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '通知客户ID',
  `new_user_status` tinyint NULL DEFAULT 1 COMMENT '新用户状态(1:新用户,0:老用户)',
  `age` int NULL DEFAULT NULL COMMENT '年龄',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `ip` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'ip地址',
  `register_device` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '注册设备',
  `active_score` int NULL DEFAULT 0 COMMENT '活跃分数',
  `active_level` int NULL DEFAULT 0 COMMENT '活跃等级',
  `active_coefficient` decimal(10, 2) NULL DEFAULT 1.00 COMMENT '活跃系数',
  `credit_score` decimal(10, 2) NULL DEFAULT 0.80 COMMENT '生态信誉分',
  `promoter_status` tinyint(1) NULL DEFAULT 0 COMMENT '推广员状态(0否 1是)',
  `job` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '职业',
  `job_type_id` bigint NULL DEFAULT NULL COMMENT '职业ID',
  `enterprise_user_id` bigint NULL DEFAULT NULL COMMENT '企业员工ID',
  `agent_status` tinyint(1) NULL DEFAULT 0 COMMENT '代理商状态(0否 1是)',
  `agent_audit_status` tinyint NULL DEFAULT -1 COMMENT '代理商审核状态（-1:未申请 0:审核中 1:审核通过 2:审核失败）',
  `agent_refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '代理商审核拒绝原因',
  `agent_audit_time` datetime NULL DEFAULT NULL COMMENT '代理商审核时间',
  `promoter_audit_status` tinyint NULL DEFAULT -1 COMMENT '推广员审核状态（-1:未申请 0:审核中 1:审核通过 2:审核失败）',
  `promoter_refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '推广员审核拒绝原因',
  `promoter_audit_time` datetime NULL DEFAULT NULL COMMENT '推广员审核时间',
  PRIMARY KEY (`account_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户账户表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for api_address
-- ----------------------------
DROP TABLE IF EXISTS `api_address`;
CREATE TABLE `api_address`  (
  `address_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收货地址ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '所在地区（包含省市区街道）',
  `detail_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `default_status` tinyint NULL DEFAULT 0 COMMENT '是否默认（0否 1是）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  PRIMARY KEY (`address_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户收货地址表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for approval_process
-- ----------------------------
DROP TABLE IF EXISTS `approval_process`;
CREATE TABLE `approval_process`  (
  `approval_process_id` bigint NOT NULL AUTO_INCREMENT COMMENT '审批流程id',
  `location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批位置',
  `identifier` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批标识符（唯一）',
  `del_flag` tinyint NULL DEFAULT 0 COMMENT '状态状态（0正常 1停用）',
  `create_by` bigint NULL DEFAULT NULL COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`approval_process_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '审批流程表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for approval_process_detail
-- ----------------------------
DROP TABLE IF EXISTS `approval_process_detail`;
CREATE TABLE `approval_process_detail`  (
  `approval_process_detail_id` bigint NOT NULL AUTO_INCREMENT COMMENT '审批流程详情id',
  `approval_process_id` bigint NULL DEFAULT NULL COMMENT '审批流程id',
  `level` tinyint NULL DEFAULT 1 COMMENT '审批等级',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审核人id',
  `identifier` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批标识符（唯一）',
  `del_flag` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NULL DEFAULT NULL COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`approval_process_detail_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 115 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '审批流程详情表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for attachments
-- ----------------------------
DROP TABLE IF EXISTS `attachments`;
CREATE TABLE `attachments`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `file_key` varchar(2047) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `height` int NULL DEFAULT 0,
  `media_type` varchar(127) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `path` varchar(1023) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `size` bigint NOT NULL,
  `suffix` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `thumb_path` varchar(1023) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `type` int NULL DEFAULT 0,
  `width` int NULL DEFAULT 0,
  `create_date` datetime NULL DEFAULT NULL,
  `update_date` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `attachments_media_type`(`media_type`) USING BTREE,
  INDEX `attachments_create_time`(`create_date`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '附件表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for attestation
-- ----------------------------
DROP TABLE IF EXISTS `attestation`;
CREATE TABLE `attestation`  (
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `attestation_type` tinyint NULL DEFAULT 0 COMMENT '认证类型(1:个人 2：企业 3:个体户 4:工作室)',
  `real_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '真实名称',
  `account_sex` tinyint NULL DEFAULT 0 COMMENT '用户性别(0:位置 1:男 2:女)',
  `account_birthday` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户生日',
  `identity_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '身份证号',
  `validity_start_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '有效开始时间',
  `validity_end_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '有效结束时间',
  `front_identity_card` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '身份证国徽面',
  `reverse_identity_card` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '身份证人像面',
  `hand_identity_card` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '手持身份身份证',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0:审核中 1:审核通过 2:审核拒绝）',
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省编码',
  `province` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市编码',
  `city` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县编码',
  `county` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `dept_id` bigint NULL DEFAULT 0 COMMENT '城市ID',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '地址',
  `address_details` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '地址详情',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  `three_serve_type_id` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '三级服务ID(多选)',
  `company_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '公司名称',
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系人名称',
  `contact_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系电话',
  `business_license` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '营业执照',
  `exam_status` tinyint NULL DEFAULT 0 COMMENT '考试状态(0:未考试 1：已通过 2未通过)',
  `one_serve_type_id` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '一级服务ID(多选)',
  `two_serve_type_id` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '二级服务ID(多选)',
  `one_serve_type_name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '一级服务名称(多选)',
  `two_serve_type_name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '二级服务名称(多选)',
  `three_serve_type_name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '三级服务名称(多选)',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '纬度',
  `account_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户头像',
  `account_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户昵称',
  `account_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户电话',
  `alternate_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '备用电话',
  `self_introduction` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '个人介绍',
  `update_one_serve_type_id` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '修改后一级服务ID(多选)',
  `update_two_serve_type_id` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '修改后二级服务ID(多选)',
  `update_three_serve_type_id` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '修改后三级服务ID(多选)',
  `update_one_serve_type_name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '修改后一级服务名称(多选)',
  `update_two_serve_type_name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '修改后二级服务名称(多选)',
  `update_three_serve_type_name` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '修改后三级服务名称(多选)',
  `certification` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '资格证(作废)',
  `certification_status` tinyint NULL DEFAULT -1 COMMENT '资格认证状态(-1:未认证,0:审核中,1:已通过,2:已拒绝)',
  `enterprise_address` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '企业地址',
  `edit_audit_status` tinyint NULL DEFAULT -1 COMMENT '编辑审核状态(-1:未编辑,0:待审核,1:已通过,2:已拒绝)',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '拒绝原因',
  `certification_refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '资格认证拒绝原因',
  `applause_rate` decimal(5, 2) NULL DEFAULT 100.00 COMMENT '好评率(%)',
  `work_status` tinyint NULL DEFAULT 0 COMMENT '工作状态(1=工作中,0=休息中)',
  `monday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周一可预约时间',
  `tuesday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周二可预约时间',
  `wednesday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周三可预约时间',
  `thursday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周四可预约时间',
  `friday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周五可预约时间',
  `saturday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周六可预约时间',
  `sunday_time_ids` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '周天可预约时间',
  `self_introduction_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '个人介绍图片',
  `total_balance_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '累计余额',
  `balance_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '剩余余额',
  `freeze_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '冻结金额',
  `withdrawal_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `bail_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '保证金金额',
  `rests_certification` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '其他资质',
  `start_work_date` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '开始工作时间',
  `expertise_field` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '擅长领域',
  PRIMARY KEY (`attestation_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '认证管理' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for attestation_certification
-- ----------------------------
DROP TABLE IF EXISTS `attestation_certification`;
CREATE TABLE `attestation_certification`  (
  `attestation_certification_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '认证资格证ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `certification_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '资格证名称',
  `certification_picture` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '资格证图片',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  PRIMARY KEY (`attestation_certification_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '认证资格证' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for banners
-- ----------------------------
DROP TABLE IF EXISTS `banners`;
CREATE TABLE `banners`  (
  `banner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '主键ID',
  `user_id` bigint NULL DEFAULT NULL COMMENT '后台用户Id',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '后台部门Id',
  `city_id` bigint NULL DEFAULT NULL COMMENT '城市Id',
  `file_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '文件类型(图片:image 视频:video)',
  `image_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '图片(一张)',
  `banner_location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'banner位置(1:首页 2:商城)',
  `source_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '来源(‘APP’)',
  `jump_type` char(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '跳转类型(0:不跳转 1:详情)',
  `jump_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '跳转地址',
  `sort_num` int NULL DEFAULT 0 COMMENT '排序(排序越大，越靠前)',
  `show_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否显示(0:不显示 1:显示)',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否删除(0:未删除 1:已删除)',
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '详情',
  `banner_type` tinyint NULL DEFAULT 0 COMMENT 'banner类型0服务',
  PRIMARY KEY (`banner_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'banner表' ROW_FORMAT = COMPACT;

-- ----------------------------
-- Table structure for black_record
-- ----------------------------
DROP TABLE IF EXISTS `black_record`;
CREATE TABLE `black_record`  (
  `black_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '拉黑记录ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `target_attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '目标认证ID',
  `target_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拉黑用户ID',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '是否删除(0：否 1：是）',
  PRIMARY KEY (`black_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '拉黑记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for business_class
-- ----------------------------
DROP TABLE IF EXISTS `business_class`;
CREATE TABLE `business_class`  (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '主键id',
  `class_code` int NOT NULL COMMENT '行业分类code',
  `class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '行业分类描述',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `create_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `update_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父类ID',
  `sort_num` int NULL DEFAULT NULL COMMENT '顺序',
  `level` int NULL DEFAULT NULL COMMENT '级别',
  `show_status` tinyint(1) NULL DEFAULT 0 COMMENT '显示状态（0隐藏 1显示）',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '行业分类表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for cash_wallet
-- ----------------------------
DROP TABLE IF EXISTS `cash_wallet`;
CREATE TABLE `cash_wallet`  (
  `cash_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '现金钱包ID',
  `account_type` tinyint(1) NULL DEFAULT NULL COMMENT '用户类型（1用户 2企业）',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户ID',
  `customer_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '客户ID',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户名称',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `total_amount` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '总收益',
  `remaining_amount` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '余额',
  `withdrawal_amount` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `frozen_amount` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '冻结金额',
  `wait_entry_amount` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '待入账金额',
  `wallet_status` tinyint(1) NULL DEFAULT 0 COMMENT '钱包状态（0正常 1冻结 2禁用）',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`cash_wallet_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '现金钱包表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for cash_wallet_transaction
-- ----------------------------
DROP TABLE IF EXISTS `cash_wallet_transaction`;
CREATE TABLE `cash_wallet_transaction`  (
  `cash_wallet_transaction_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '现金钱包交易流水ID',
  `cash_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '现金钱包ID',
  `account_type` tinyint(1) NULL DEFAULT NULL COMMENT '用户类型（1用户 2企业）',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户ID',
  `customer_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '客户ID',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户名称',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `transaction_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '交易单号',
  `transaction_type` tinyint NULL DEFAULT NULL COMMENT '交易类型（1充值 2消费扣款 3退款 4提现 5冻结 6解冻 7奖励 8扣罚 9待入账 10入账）',
  `income_expense_type` tinyint(1) NULL DEFAULT NULL COMMENT '收入或支出（1-收入 2-支出）',
  `channel_type` tinyint(1) NULL DEFAULT 1 COMMENT '渠道类型（1-线上 2-线下）',
  `transaction_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '交易名称',
  `amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易金额',
  `before_remaining_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前余额（对应 remaining_amount）',
  `after_remaining_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后余额（对应 remaining_amount）',
  `before_frozen_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前冻结金额（对应 frozen_amount）',
  `after_frozen_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后冻结金额（对应 frozen_amount）',
  `before_wait_entry_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前待入账金额（对应 wait_entry_amount）',
  `after_wait_entry_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后待入账金额（对应 wait_entry_amount）',
  `before_total_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前总收益（对应 total_amount）',
  `after_total_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后总收益（对应 total_amount）',
  `related_biz_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '关联业务单号（如订单号、退款单号等）',
  `related_biz_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '关联业务类型（order订单 refund退款 withdraw提现 transfer转账）',
  `order_type` tinyint NULL DEFAULT NULL COMMENT '订单类型（1商城订单）',
  `transaction_status` tinyint(1) NULL DEFAULT 0 COMMENT '交易状态（0待处理 1成功 2失败 3撤销）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '交易备注',
  `transaction_time` datetime NULL DEFAULT NULL COMMENT '交易完成时间',
  `source_app_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '来源APP名称',
  `source_app_logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '来源APPlogo',
  `transaction_detail` json NULL COMMENT '交易详情',
  `operator` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '操作人',
  `operator_id` bigint NULL DEFAULT NULL COMMENT '操作人ID',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`cash_wallet_transaction_id`) USING BTREE,
  INDEX `idx_cash_wallet_id`(`cash_wallet_id`) USING BTREE COMMENT '现金钱包ID索引',
  INDEX `idx_global_account_id`(`account_id`) USING BTREE COMMENT '全局用户ID索引',
  INDEX `idx_customer_id`(`customer_id`) USING BTREE COMMENT '客户ID索引',
  INDEX `idx_account_type`(`account_type`) USING BTREE COMMENT '用户类型索引',
  INDEX `idx_transaction_type`(`transaction_type`) USING BTREE COMMENT '交易类型索引',
  INDEX `idx_transaction_status`(`transaction_status`) USING BTREE COMMENT '交易状态索引',
  INDEX `idx_related_biz_no`(`related_biz_no`) USING BTREE COMMENT '关联业务单号索引',
  INDEX `idx_create_time`(`create_time`) USING BTREE COMMENT '创建时间索引',
  INDEX `idx_transaction_time`(`transaction_time`) USING BTREE COMMENT '交易时间索引',
  INDEX `idx_wallet_type_status`(`cash_wallet_id`, `transaction_type`, `transaction_status`) USING BTREE COMMENT '钱包-类型-状态联合索引',
  INDEX `idx_account_create_time`(`account_id`, `create_time`) USING BTREE COMMENT '用户-创建时间联合索引',
  INDEX `idx_customer_create_time`(`customer_id`, `create_time`) USING BTREE COMMENT '客户-创建时间联合索引',
  INDEX `idx_transaction_no`(`transaction_no`) USING BTREE COMMENT '交易单号唯一索引'
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '现金钱包交易流水表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for client_record
-- ----------------------------
DROP TABLE IF EXISTS `client_record`;
CREATE TABLE `client_record`  (
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行',
  `open_bank_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行账号账号',
  `duty_paragraph` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '税号',
  `contact_person` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `remarks` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '是否删除(0:未删除 1:已删除)',
  `payment_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未支付金额',
  `paid_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已支付金额',
  `not_invoice_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未开票金额',
  `invoice_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已开票金额',
  `detail_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `industry` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '行业',
  `joint_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联户号',
  `category` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '类别',
  `bank_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联行号',
  `esign_certification_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝认证状态(-1未认证 0认证中 1认证成功)',
  `esign_authorization_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝授权状态(-1未授权 0授权中 1授权成功)',
  `esign_authorization_deadline_time` datetime NULL DEFAULT NULL COMMENT 'e签宝授权截止日期',
  `auth_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '认证授权流程ID',
  `auth_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证授权长链接',
  `auth_short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证授权短链接',
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构账号ID',
  `authorized_scopes` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '授权范围',
  `core_status` tinyint NULL DEFAULT 0 COMMENT '核心状态(0否 1是)',
  `core_remarks` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '核心客户备注',
  `one_business_class_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '一级行业分类ID',
  `one_business_class_name` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '一级行业分类名称',
  `two_business_class_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '二级行业分类ID',
  `two_business_class_name` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '二级分类名称',
  `three_business_class_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '三级行业分类ID',
  `three_business_class_name` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '三年级行业分类名称',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `customer_size_type` int NULL DEFAULT NULL COMMENT '客户规模(1微型企业 2小型企业 3中型企业 4大型企业)',
  `customer_type` int NULL DEFAULT 2 COMMENT '客户类型(1个人客户 2企业客户)',
  PRIMARY KEY (`client_record_id`) USING BTREE,
  INDEX `index_client_name`(`client_name`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '客户表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for collection_record
-- ----------------------------
DROP TABLE IF EXISTS `collection_record`;
CREATE TABLE `collection_record`  (
  `collection_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收藏记录ID',
  `collection_type` tinyint NULL DEFAULT NULL COMMENT '收藏类型（1店铺 2商品 3视频 ）',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '对应的主键ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  PRIMARY KEY (`collection_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收藏记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for comment
-- ----------------------------
DROP TABLE IF EXISTS `comment`;
CREATE TABLE `comment`  (
  `comment_id` bigint NOT NULL AUTO_INCREMENT COMMENT '评论ID',
  `forum_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '论坛信息ID',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '回复对象ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `account_head` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '用户头像',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户昵称',
  `comment_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '评论内容',
  `audit_status` tinyint NULL DEFAULT 1 COMMENT '审核状态（0待审核 1已通过 2已拒绝）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `ancestor_id` bigint NULL DEFAULT 0 COMMENT '评论祖类Id',
  PRIMARY KEY (`comment_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 50 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '视频评论表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for connect_microphone_record
-- ----------------------------
DROP TABLE IF EXISTS `connect_microphone_record`;
CREATE TABLE `connect_microphone_record`  (
  `connect_microphone_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '连麦记录ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `head_portrait` varchar(255) CHARACTER SET utf32 COLLATE utf32_general_ci NULL DEFAULT NULL COMMENT '头像',
  `nick_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '昵称',
  `target_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主播用户ID',
  `target_head_portrait` varchar(255) CHARACTER SET utf32 COLLATE utf32_general_ci NULL DEFAULT NULL COMMENT '主播用户头像',
  `target_nick_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主播用户昵称',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0审核中 1已通过 2已拒绝 3已过期 4已结束）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `img_video_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播间ID',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `end_time` datetime NULL DEFAULT NULL COMMENT '结束时间',
  `duration` bigint NULL DEFAULT NULL COMMENT '连麦时长(秒)',
  `connect_type` tinyint NULL DEFAULT 1 COMMENT '连麦类型（1用户申请 2主播邀请）',
  PRIMARY KEY (`connect_microphone_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '连麦记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for contract
-- ----------------------------
DROP TABLE IF EXISTS `contract`;
CREATE TABLE `contract`  (
  `contract_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '合同ID',
  `contract_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同名称',
  `contract_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `template_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同模板ID',
  `template_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同模板名称',
  `sign_subject` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署主题',
  `sign_deadline` datetime NULL DEFAULT NULL COMMENT '签署截止时间',
  `is_draft` tinyint NULL DEFAULT 0 COMMENT '是否为草稿 (0-否, 1-是)',
  `psn_signer_info` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '个人签署方信息',
  `org_signer_info` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '机构签署方信息',
  `notify_seal_approver` tinyint NULL DEFAULT 0 COMMENT '通知企业印章用印审批人员 (0-否, 1-是)',
  `is_confidential` tinyint NULL DEFAULT 0 COMMENT '是否保密 (0-否, 1-是)',
  `can_cancel` tinyint NULL DEFAULT 1 COMMENT '是否可以解约 (0-否, 1-是)',
  `contract_expiry_date` datetime NULL DEFAULT NULL COMMENT '合同到期时间',
  `file_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '文件ID',
  `approval_status` tinyint NULL DEFAULT 0 COMMENT '审批状态 ( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `sign_status` tinyint NULL DEFAULT 0 COMMENT '签署状态 (0-未开始, 1-签署中, 2-已完成, 3-已撤销 5-已过期 7-已拒签)',
  `user_id` bigint NULL DEFAULT NULL COMMENT '创建用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '创建部门ID',
  `dept_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建部门名称',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `principal_people` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '负责人',
  `file_download_url` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '文件下载地址',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `remarks` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '备注',
  `psn_initiator_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '个人发起方账号ID',
  `initiator_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起方机构ID',
  `initiator_psn_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起方经办人账号ID',
  `initiator_user_id` bigint NULL DEFAULT NULL COMMENT '发起方用户ID',
  `initiator_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起方用户名称',
  `initiator_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起方用户电话',
  `initiator_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起方用户头像',
  `initiator_type` tinyint NULL DEFAULT NULL COMMENT '发起方类型 (0-个人, 1-机构, 2-法定代表人)',
  `initiator_info` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '发起方信息JSON',
  `notice_types` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署通知类型(1 - 短信通知 2 - 邮件通知 3 - 钉钉工作通知 5 - 微信通知 6 - 企业微信通知 7 - 飞书通知)',
  `components` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '合同控件信息',
  `sign_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署流程ID',
  `sign_refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署拒绝原因',
  `sign_flow_create_time` datetime NULL DEFAULT NULL COMMENT '签署流程创建时间',
  `sign_flow_start_time` datetime NULL DEFAULT NULL COMMENT '签署流程开启时间',
  `sign_flow_finish_time` datetime NULL DEFAULT NULL COMMENT '签署流程完结时间',
  `initiator_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起方机构名称',
  `sign_file_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署文件ID',
  `sign_file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署文件名称',
  `sign_download_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '已签署文件下载链接',
  `revoke_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '撤销原因',
  PRIMARY KEY (`contract_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '电子合同表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for contract_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `contract_copy_record`;
CREATE TABLE `contract_copy_record`  (
  `contract_copy_record_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '抄送人ID',
  `contract_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同ID',
  `psn_account` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送人账号 (手机号/邮箱)',
  `cc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送人姓名',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `view_status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '已查阅状态 (0-未查阅, 1-已查阅)',
  `view_time` datetime NULL DEFAULT NULL COMMENT '查阅时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构账号ID',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`contract_copy_record_id`) USING BTREE,
  INDEX `idx_contract_id`(`contract_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '合同抄送人表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for contract_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `contract_examine_flow`;
CREATE TABLE `contract_examine_flow`  (
  `contract_examine_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '合同审批流程ID',
  `contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `contract_examine_type` tinyint NULL DEFAULT 1 COMMENT '合同审批类型（1：生成合同 2：修改合同）',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`contract_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '合同审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for contract_signer
-- ----------------------------
DROP TABLE IF EXISTS `contract_signer`;
CREATE TABLE `contract_signer`  (
  `contract_signer_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '签署方ID',
  `contract_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同ID',
  `signer_type` tinyint(1) NULL DEFAULT 0 COMMENT '签署方类型 (0-个人, 1-机构, 2-法定代表人,3 - 经办人)',
  `signer_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署方姓名/机构名称',
  `signer_account` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署方账号信息 (手机号/邮箱)',
  `sign_status` tinyint NULL DEFAULT 0 COMMENT '签署状态 (0-未开始, 1-签署中, 2-已完成, 3-已撤销 5-已过期 7-已拒签)',
  `signed_time` datetime NULL DEFAULT NULL COMMENT '签署时间',
  `sign_order` int NULL DEFAULT 1 COMMENT '签署顺序',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构账号ID',
  `psn_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经办人账号ID',
  `psn_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '个人账号标识（手机号或邮箱）用于登录e签宝官网的凭证',
  `psn_account_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经办人姓名',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒签原因',
  `short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署短链接（有效期180天）',
  `url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '签署长链接（永久有效）',
  PRIMARY KEY (`contract_signer_id`) USING BTREE,
  INDEX `idx_contract_id`(`contract_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '合同签署方表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for contract_template
-- ----------------------------
DROP TABLE IF EXISTS `contract_template`;
CREATE TABLE `contract_template`  (
  `contract_template_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '合同模板ID',
  `template_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '模板名称',
  `class_code` int NULL DEFAULT NULL COMMENT '行业分类code',
  `class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '行业分类描述',
  `file_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '文件ID',
  `file_upload_url` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '文件上传地址，链接有效期60分钟。',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `create_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `update_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  `file_upload_status` tinyint NULL DEFAULT 0 COMMENT '文件上传状态(0 - 文件未上传\n\n1 - 文件上传中\n\n2 - 文件上传已完成 或 文件已转换（HTML）\n\n3 - 文件上传失败\n\n4 - 文件等待转换（PDF）\n\n5 - 文件已转换（PDF）\n\n6 - 加水印中\n\n7 - 加水印完毕\n\n8 - 文件转化中（PDF）\n\n9 - 文件转换失败（PDF）\n\n10 - 文件等待转换（HTML）\n\n11 - 文件转换中（HTML）\n\n12 - 文件转换失败（HTML）)',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '文件名称',
  `file_size` int NULL DEFAULT NULL COMMENT '文件大小',
  `file_download_url` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '文件下载地址',
  `file_total_page_count` int NULL DEFAULT NULL COMMENT 'pdf文件总页数',
  `page_width` float NULL DEFAULT NULL COMMENT '首页宽度，单位：像素（px）',
  `page_height` float NULL DEFAULT NULL COMMENT '首页高度，单位：像素（px）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0否 1是)',
  `file_url` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '二进制文件',
  `doc_template_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '合同模板ID',
  `doc_template_create_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '制作合同模板的页面短链接',
  `doc_template_create_long_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '制作合同模板的页面长链接',
  `create_status` tinyint NULL DEFAULT 0 COMMENT '制作状态(0未制作 1已制作)',
  `doc_template_expire_time` datetime NULL DEFAULT NULL COMMENT '模版过期时间',
  `doc_template_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '文件模板名称',
  `doc_template_edit_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '编辑文件模板的页面短链接',
  `doc_template_edit_long_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '编辑文件模板的页面长链接',
  `doc_template_edit_expire_time` datetime NULL DEFAULT NULL COMMENT '编辑文件模板过期时间',
  `doc_template_preview_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '预览文件模板页面链接，有效期30分钟，过期可以重新获取',
  `share_status` tinyint(1) NULL DEFAULT 0 COMMENT '共享状态(0不共享 1共享)',
  `source_type` int NULL DEFAULT NULL COMMENT '来源类型(1内部 2共享)',
  `new_doc_template_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '新的模板ID',
  PRIMARY KEY (`contract_template_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '合同模板' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for cost_record
-- ----------------------------
DROP TABLE IF EXISTS `cost_record`;
CREATE TABLE `cost_record`  (
  `cost_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '费用管理id',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `cost_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务费类型',
  `cost_type_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务费类型id',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `actual_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '实际金额',
  `tax_rate` decimal(5, 2) NULL DEFAULT 0.00 COMMENT '税率（例如13.00表示13%）',
  `calculated_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '核算金额',
  `payable_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '应付账款',
  `uninvoiced_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '欠票金额',
  `received_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '收票合计',
  `payment_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '付款合计',
  `sort_num` int NULL DEFAULT NULL COMMENT '排序号',
  `can_deleted` tinyint NULL DEFAULT 0 COMMENT '是否可删除（前端用）',
  `del_flag` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `statement_status` tinyint NULL DEFAULT 0 COMMENT '结算状态(0:未结算 1:结算中 2:已结算)',
  `invoice_status` tinyint NULL DEFAULT 0 COMMENT '发票状态(0:未开票 1:开票中 2已开票)',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  PRIMARY KEY (`cost_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '费用管理' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for coupon
-- ----------------------------
DROP TABLE IF EXISTS `coupon`;
CREATE TABLE `coupon`  (
  `coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '优惠券ID',
  `user_id` bigint NULL DEFAULT NULL COMMENT '后台用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `coupon_source` tinyint(1) NULL DEFAULT NULL COMMENT '优惠券来源（1平台 2商家）',
  `coupon_module` tinyint(1) NULL DEFAULT 0 COMMENT '优惠券模块（1商城 2服务）',
  `coupon_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '优惠券名称',
  `coupon_type` tinyint(1) NULL DEFAULT 1 COMMENT '优惠券类型（1满减 2立减）',
  `use_scope` tinyint(1) NULL DEFAULT 0 COMMENT '使用范围（0全场通用 1分类通用 2店铺使用 3指定商品）',
  `class_ids` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '指定分类ID',
  `class_names` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '指定分类名称',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '店铺ID',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '店铺名称',
  `primary_ids` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '指定ID',
  `primary_names` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '指定名称',
  `full_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '满值',
  `reduce_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '立减值',
  `issue_start_time` date NULL DEFAULT NULL COMMENT '发放开始时间',
  `issue_end_time` date NULL DEFAULT NULL COMMENT '发放结束时间',
  `valid_type` tinyint(1) NULL DEFAULT NULL COMMENT '有效期类型（1领取后生效 2指定日期）',
  `valid_days` int NULL DEFAULT NULL COMMENT '有效天数',
  `start_time` date NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` date NULL DEFAULT NULL COMMENT '结束时间',
  `coupon_num` int NULL DEFAULT 1 COMMENT '优惠券数量',
  `surplus_num` int NULL DEFAULT 0 COMMENT '优惠券剩余数量',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `cross_platform_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否跨平台（0否 1是）',
  `platform_type` tinyint(1) NULL DEFAULT 1 COMMENT '平台类型（1发券方 2渠道方）',
  `commission_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '佣金比例(%)',
  `original_coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原优惠券ID',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '来源项目ID',
  `original_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '来源项目名称',
  `original_project_logo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '来源项目logo',
  `target_project_ids` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '目标项目ID',
  `target_project_names` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '目标项目名称',
  `parent_class_ids` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '父级分类ID',
  `class_ids_json` json NULL COMMENT '分类IDJSON(级联选择器回显使用)',
  `discount_value` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '折扣值(0-10)',
  `receive_count` int NULL DEFAULT 0 COMMENT '领用数量',
  `project_type` tinyint NULL DEFAULT 1 COMMENT '项目类型(1=商城项目,2=服务项目）',
  `project_type_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '项目类型名称',
  PRIMARY KEY (`coupon_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '优惠券表' ROW_FORMAT = COMPACT;

-- ----------------------------
-- Table structure for data_bank
-- ----------------------------
DROP TABLE IF EXISTS `data_bank`;
CREATE TABLE `data_bank`  (
  `data_bank_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '资料库ID',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类别',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态 0：显示 1：隐藏',
  `sort_num` bigint NULL DEFAULT 1 COMMENT '排序，数字越小越靠前',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `safety_stock_num` int NULL DEFAULT 0 COMMENT '安全库存数量',
  `max_stock_num` int NULL DEFAULT 0 COMMENT '最高库存数量',
  PRIMARY KEY (`data_bank_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '物资库' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for earning_record
-- ----------------------------
DROP TABLE IF EXISTS `earning_record`;
CREATE TABLE `earning_record`  (
  `earning_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '收益记录ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `earning_title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '收益标题',
  `earning_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '收益金额',
  `source_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '来源ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  PRIMARY KEY (`earning_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收益记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for edit_attestation
-- ----------------------------
DROP TABLE IF EXISTS `edit_attestation`;
CREATE TABLE `edit_attestation`  (
  `edit_attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '修改认证ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `attestation_type` tinyint NULL DEFAULT 0 COMMENT '认证类型(1:个人 2：企业 3:个体户 4:工作室)',
  `real_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '真实名称',
  `account_sex` tinyint NULL DEFAULT 0 COMMENT '用户性别(0:位置 1:男 2:女)',
  `account_birthday` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户生日',
  `identity_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '身份证号',
  `validity_start_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '有效开始时间',
  `validity_end_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '有效结束时间',
  `front_identity_card` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '身份证国徽面',
  `reverse_identity_card` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '身份证人像面',
  `hand_identity_card` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '手持身份身份证',
  `company_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '公司名称',
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系人名称',
  `contact_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系电话',
  `business_license` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '营业执照',
  `enterprise_address` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '企业地址',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0:审核中 1:审核通过 2:审核拒绝）',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '拒绝原因',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  `rests_certification` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '其他资质',
  `start_work_date` date NULL DEFAULT NULL COMMENT '开始工作时间',
  `expertise_field` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '擅长领域',
  PRIMARY KEY (`edit_attestation_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '修改认证' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for esign_auth_flow
-- ----------------------------
DROP TABLE IF EXISTS `esign_auth_flow`;
CREATE TABLE `esign_auth_flow`  (
  `esign_auth_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'e签宝认证流程ID',
  `auth_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户认证&授权流程ID',
  `primary_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '主键ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `auth_type` tinyint NULL DEFAULT NULL COMMENT '类型(1部门 2客户 3供应商)',
  `esign_certification_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝认证状态(-1未认证 0认证中 1认证成功)',
  `esign_authorization_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝授权状态(-1未授权 0授权中 1授权成功)',
  `esign_authorization_deadline_time` datetime NULL DEFAULT NULL COMMENT 'e签宝授权截止日期',
  `auth_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证授权长链接',
  `auth_short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证授权短链接',
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构账号ID',
  `org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '机构账号',
  PRIMARY KEY (`esign_auth_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = 'e签宝认证流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for esign_auth_scope_detail
-- ----------------------------
DROP TABLE IF EXISTS `esign_auth_scope_detail`;
CREATE TABLE `esign_auth_scope_detail`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'e签宝授权范围明细ID',
  `auth_flow_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '认证流程ID',
  `primary_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '主键ID',
  `auth_type` int NULL DEFAULT NULL COMMENT '认证类型',
  `authorized_scope` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '授权范围',
  `effective_time` datetime NULL DEFAULT NULL COMMENT '生效时间',
  `expire_time` datetime NULL DEFAULT NULL COMMENT '失效时间',
  `auth_status` int NULL DEFAULT -1 COMMENT '授权状态(-1未授权 0授权中 1授权成功)',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_auth_flow_id`(`auth_flow_id`) USING BTREE,
  INDEX `idx_primary_id`(`primary_id`) USING BTREE,
  INDEX `idx_authorized_scope`(`authorized_scope`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 91 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = 'e签宝授权范围明细表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for examine_initiate
-- ----------------------------
DROP TABLE IF EXISTS `examine_initiate`;
CREATE TABLE `examine_initiate`  (
  `examine_initiate_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '审批发起ID',
  `examine_module_id` bigint NULL DEFAULT NULL COMMENT '审批类型ID  1：补卡申请 2：报销 3：用印申请 4：请假 5：请款 6：采购 7： 用车',
  `start_time` datetime NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime NULL DEFAULT NULL COMMENT '结束时间',
  `ask_for_leave_hour` double(10, 2) NULL DEFAULT NULL COMMENT '请假时长(天)',
  `reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '请假事由/报销事由/合同说明/申请内容/补卡理由',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '图片,多个以逗号隔开',
  `reimburse_money` decimal(10, 2) NULL DEFAULT NULL COMMENT '报销金额(元)',
  `money_date` date NULL DEFAULT NULL COMMENT '费用发生时间',
  `total_money` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '总报销金额/合同总额(元)',
  `parent_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '父类ID',
  `contract_text` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同正文',
  `contract_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同名称',
  `contract_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `contract_money_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同金额类型',
  `contract_deadline_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同期限类型',
  `signature_date` date NULL DEFAULT NULL COMMENT '合同签署日期',
  `seal_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '印章类型',
  `content` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批详情',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `leave_type` varchar(64) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NULL DEFAULT NULL COMMENT '请假类型',
  `user_id` bigint NULL DEFAULT NULL COMMENT '发起者ID',
  `expense_type` tinyint NULL DEFAULT NULL COMMENT '报销类型（1：差旅费 2：招待费 3:其他 ）',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发起者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '发起者所属部门ID',
  `company_id` bigint NULL DEFAULT NULL COMMENT '发起者所属公司ID',
  `reissue_clocking_date` date NULL DEFAULT NULL COMMENT '补卡日期',
  `raw_clocking_time` datetime NULL DEFAULT NULL COMMENT '原打卡时间',
  `reissue_clocking_time` datetime NULL DEFAULT NULL COMMENT '补卡时间',
  `clocking_status` tinyint NULL DEFAULT NULL COMMENT '1：上班打卡 2：下班打卡',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `finish_time` datetime NULL DEFAULT NULL COMMENT '审核完成时间',
  `travel_itinerary_json` json NULL COMMENT '差旅费 - 行程明细 json',
  `travel_subsidy_json` json NULL COMMENT '差旅费 - 出差补贴 json',
  `travel_other_json` json NULL COMMENT '差旅费 - 其他项目 json',
  `evidence_json` json NULL COMMENT '凭证文件 json',
  `travel_user_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出差人',
  `cash_out_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '请款编号',
  `remarks` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `entertainment_dept_id` bigint NULL DEFAULT NULL COMMENT '招待费 - 招待部门ID',
  `entertainment_dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '招待费 - 招待部门名称',
  `responsible_person` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '招待费 - 经办人',
  `entertainment_guest` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '招待费 - 招待对象',
  `guest_count` int NULL DEFAULT NULL COMMENT '招待费 - 客人人数',
  `accompany_count` int NULL DEFAULT NULL COMMENT '招待费 - 陪同人数',
  `entertainment_details_json` json NULL COMMENT '招待费 - 报销明细',
  `use_seal_dept_id` bigint NULL DEFAULT NULL COMMENT '用印部门ID',
  `use_seal_dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用印部门名称',
  `use_seal_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用印日期',
  `use_seal_file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用印文件名称',
  `use_seal_file_count` int NULL DEFAULT NULL COMMENT '用印文件数量',
  `use_seal_file_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用印文件类型',
  `cash_out_money` decimal(10, 2) NULL DEFAULT NULL COMMENT '请款金额',
  `payment_method` tinyint NULL DEFAULT NULL COMMENT '付款方式（1：转账  2：现金）',
  `payee` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '收款人',
  `opening_bank` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行',
  `bank_account` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行账号',
  `cash_out_ids` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '请款编号 (多个用，分割)',
  `repaid_amount` decimal(10, 2) NULL DEFAULT NULL COMMENT '待还款金额',
  `cancel_amount` decimal(10, 2) NULL DEFAULT NULL COMMENT '冲抵金额',
  `apply_dept_id` bigint NULL DEFAULT NULL COMMENT '申请部门ID',
  `apply_dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '申请部门名称',
  `project_ids` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目ID(多个用，隔开)',
  `cash_out_time` datetime NULL DEFAULT NULL COMMENT '支付日期(请款)',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `reject_pics` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝图片',
  `destination` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出差目的地',
  `startPoint` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出差起始地',
  `other_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '其他费用报销',
  `purchase_dept_id` bigint NULL DEFAULT NULL COMMENT '采购部门ID',
  `purchase_dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购部门名称',
  `purchase_person` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购人',
  `purchase_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '采购明细',
  `car_dept_id` bigint NULL DEFAULT NULL COMMENT '用车部门ID',
  `car_dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用车部门名称',
  `car_person` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用车人',
  `car_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '用车明细',
  `real_start_time` datetime NULL DEFAULT NULL COMMENT '真实的请假开始时间',
  `real_end_time` datetime NULL DEFAULT NULL COMMENT '真实的请假结束时间',
  PRIMARY KEY (`examine_initiate_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '审批发起表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for examine_module
-- ----------------------------
DROP TABLE IF EXISTS `examine_module`;
CREATE TABLE `examine_module`  (
  `examine_module_id` bigint NOT NULL AUTO_INCREMENT COMMENT '审批类型ID',
  `module_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '模块名称',
  `icon` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '图标',
  `sort_num` int NULL DEFAULT 0 COMMENT '排序',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '是否显示(0:不显示 1:显示)',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`examine_module_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 45 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '审批类型表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for flow
-- ----------------------------
DROP TABLE IF EXISTS `flow`;
CREATE TABLE `flow`  (
  `flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流转表id',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '合同金额合计',
  `unit_nature` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位性质',
  `paid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已付金额合计',
  `unpaid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未付金额合计',
  `paid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已开票金额',
  `unpaid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未开票金额',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位名称',
  PRIMARY KEY (`flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '流转表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for flow_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `flow_copy_record`;
CREATE TABLE `flow_copy_record`  (
  `flow_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流转抄送记录',
  `flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`flow_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '流转抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for flow_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `flow_examine_flow`;
CREATE TABLE `flow_examine_flow`  (
  `flow_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流转审批流程ID',
  `flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`flow_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '流转审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for follow_record
-- ----------------------------
DROP TABLE IF EXISTS `follow_record`;
CREATE TABLE `follow_record`  (
  `follow_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '关注记录ID',
  `follow_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '被关注的用户ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  PRIMARY KEY (`follow_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '关注记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for freight_template
-- ----------------------------
DROP TABLE IF EXISTS `freight_template`;
CREATE TABLE `freight_template`  (
  `freight_template_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '商城运费模板ID',
  `template_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板名称',
  `billing_method` int NOT NULL DEFAULT 1 COMMENT '计费方式（1按件数 2按重量）',
  `sort_num` int NOT NULL DEFAULT 0 COMMENT '排序(越小越靠前)',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '店铺ID',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0否 1已删除）',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `default_status` tinyint NULL DEFAULT 0 COMMENT '默认状态（0否 1默认）',
  `distribution_status` tinyint NULL DEFAULT 0 COMMENT ' 配送状态（0否 1是）',
  `number_weight` decimal(10, 2) NULL DEFAULT 1.00 COMMENT '件数/首重(个/kg)',
  `number_weight_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '运费(元)',
  `continued_number_weight` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '续件/续重(个/kg)',
  `continued_number_weight_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '续费(元)',
  PRIMARY KEY (`freight_template_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商城运费模板' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for freight_template_city
-- ----------------------------
DROP TABLE IF EXISTS `freight_template_city`;
CREATE TABLE `freight_template_city`  (
  `freight_template_city_id` bigint NOT NULL AUTO_INCREMENT COMMENT '运费模板城市ID',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父级id',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '城市名称',
  `center` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '中心坐标',
  `citycode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'citycode',
  `adcode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'adcode',
  `level` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '级别（province:省 city:市 district:行政区）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0否 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`freight_template_city_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3693 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '运费模板城市表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for freight_template_data
-- ----------------------------
DROP TABLE IF EXISTS `freight_template_data`;
CREATE TABLE `freight_template_data`  (
  `freight_template_data_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '运费ID',
  `freight_template_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运费模板id',
  `number_weight` decimal(10, 2) NULL DEFAULT 1.00 COMMENT '件数/首重(个/kg)',
  `number_weight_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '运费(元)',
  `continued_number_weight` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '续件/续重(个/kg)',
  `continued_number_weight_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '续费(元)',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '店铺ID',
  `freight_template_city_ids` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '运费模板城市IDs',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '每次更新的标识',
  `distribution_status` tinyint NULL DEFAULT 0 COMMENT '是否不发货（0否 1是）',
  PRIMARY KEY (`freight_template_data_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '运费' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for frequency
-- ----------------------------
DROP TABLE IF EXISTS `frequency`;
CREATE TABLE `frequency`  (
  `frequency_id` bigint NOT NULL AUTO_INCREMENT COMMENT '下单频次记录ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '名称',
  `min_num` int NULL DEFAULT NULL COMMENT '最小数量天数',
  `max_num` int NULL DEFAULT NULL COMMENT '最大数量天数',
  PRIMARY KEY (`frequency_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '下单频次记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for gen_table
-- ----------------------------
DROP TABLE IF EXISTS `gen_table`;
CREATE TABLE `gen_table`  (
  `table_id` bigint NOT NULL AUTO_INCREMENT COMMENT '编号',
  `table_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '表名称',
  `table_comment` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '表描述',
  `sub_table_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '关联子表的表名',
  `sub_table_fk_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '子表关联的外键名',
  `class_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '实体类名称',
  `tpl_category` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'crud' COMMENT '使用的模板（crud单表操作 tree树表操作）',
  `tpl_web_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '前端模板类型（element-ui模版 element-plus模版）',
  `package_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '生成包路径',
  `module_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '生成模块名',
  `business_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '生成业务名',
  `function_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '生成功能名',
  `function_author` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '生成功能作者',
  `gen_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '生成代码方式（0zip压缩包 1自定义路径）',
  `gen_path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '/' COMMENT '生成路径（不填默认项目路径）',
  `options` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '其它生成选项',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`table_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 50 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '代码生成业务表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for gen_table_column
-- ----------------------------
DROP TABLE IF EXISTS `gen_table_column`;
CREATE TABLE `gen_table_column`  (
  `column_id` bigint NOT NULL AUTO_INCREMENT COMMENT '编号',
  `table_id` bigint NULL DEFAULT NULL COMMENT '归属表编号',
  `column_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '列名称',
  `column_comment` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '列描述',
  `column_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '列类型',
  `java_type` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'JAVA类型',
  `java_field` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'JAVA字段名',
  `is_pk` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否主键（1是）',
  `is_increment` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否自增（1是）',
  `is_required` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否必填（1是）',
  `is_insert` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否为插入字段（1是）',
  `is_edit` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否编辑字段（1是）',
  `is_list` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否列表字段（1是）',
  `is_query` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '是否查询字段（1是）',
  `query_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'EQ' COMMENT '查询方式（等于、不等于、大于、小于、范围）',
  `html_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '显示类型（文本框、文本域、下拉框、复选框、单选框、日期控件）',
  `dict_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '字典类型',
  `sort` int NULL DEFAULT NULL COMMENT '排序',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`column_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1264 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '代码生成业务表字段' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for gift
-- ----------------------------
DROP TABLE IF EXISTS `gift`;
CREATE TABLE `gift`  (
  `gift_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '礼物id',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '名称',
  `icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '图标',
  `gift_type` tinyint NULL DEFAULT 0 COMMENT '礼物类型（0:普通礼物）',
  `amount` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '金额',
  `sort_num` int NULL DEFAULT 0 COMMENT '排序',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否删除(0:未删除 1:已删除)',
  `special_effects` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '礼物特效',
  `special_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否特效礼物(0:不是 1:是)',
  PRIMARY KEY (`gift_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '礼物信息' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for group_buying
-- ----------------------------
DROP TABLE IF EXISTS `group_buying`;
CREATE TABLE `group_buying`  (
  `group_buying_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '主键id',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '店铺id',
  `store_goods_ids` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '商品ids',
  `store_goods_spec_ids` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '商品规格ids',
  `goods_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '商品名称',
  PRIMARY KEY (`group_buying_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '团购表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for guarantee
-- ----------------------------
DROP TABLE IF EXISTS `guarantee`;
CREATE TABLE `guarantee`  (
  `guarantee_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '保障ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保障名称',
  `order_num` int NULL DEFAULT NULL COMMENT '排序',
  `content` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保障内容',
  `guarantee_type` tinyint NULL DEFAULT NULL COMMENT '保障类型（1商品）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`guarantee_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '保障表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for holidays
-- ----------------------------
DROP TABLE IF EXISTS `holidays`;
CREATE TABLE `holidays`  (
  `holidays_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '节假日ID',
  `holidays_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '节假名称',
  `holidays_date` date NULL DEFAULT NULL COMMENT '节假日期',
  `holidays_wage` int NULL DEFAULT NULL COMMENT '节假日工资倍数',
  `holidays_status` tinyint NULL DEFAULT NULL COMMENT '节假日类型 0:补班 1:节假日',
  `target` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '调休目标',
  `after_status` tinyint NULL DEFAULT NULL COMMENT '调休类型 0:表示先调休再放假 1:表示放完假后调休',
  `rest` int NULL DEFAULT NULL COMMENT '距离调休目标天数',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建日期',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新日期',
  PRIMARY KEY (`holidays_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '节假日表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for hot_update_wgt
-- ----------------------------
DROP TABLE IF EXISTS `hot_update_wgt`;
CREATE TABLE `hot_update_wgt`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `version_code` bigint NOT NULL COMMENT '版本号',
  `download_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '更新的路径',
  `version_info` varchar(550) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '版本描述',
  `version_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '版本名称',
  `update_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'forcibly = 强制更新, solicit = 弹窗确认更新, silent = 静默更新',
  `type` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '1101:安卓 1102:ios',
  `open_status` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '1' COMMENT '该版本开放状态',
  `create_time` datetime NOT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '创建时间',
  `is_apk` tinyint NULL DEFAULT 0 COMMENT '是否整包更新 0否 1是',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 20 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '热更新' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for in_bound
-- ----------------------------
DROP TABLE IF EXISTS `in_bound`;
CREATE TABLE `in_bound`  (
  `in_bound_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '入库记录id',
  `purchase_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购编号',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类别',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态 0：显示 1：隐藏',
  `sort_num` bigint NULL DEFAULT 1 COMMENT '排序，数字越小越靠前',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `in_bound_status` tinyint NULL DEFAULT 0 COMMENT '入库状态(0:待入库 1：已入库 )',
  `purchase_date` datetime NULL DEFAULT NULL COMMENT '进货日期',
  `logistics_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流方式',
  `warehouse_time` datetime NULL DEFAULT NULL COMMENT '入库时间',
  `warehouse_detail_type` tinyint NULL DEFAULT 1 COMMENT '入库类型(1:采购入库 2：退换货入库)',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存数量',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `sales_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退货的销售详情ID',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `data_bank_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '资料库ID',
  PRIMARY KEY (`in_bound_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '入库记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for industry_trend_statistics
-- ----------------------------
DROP TABLE IF EXISTS `industry_trend_statistics`;
CREATE TABLE `industry_trend_statistics`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `industry_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '行业编码',
  `industry_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '行业名称',
  `product_category` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '产品分类（可选，用于细分行业）',
  `quarter_year` int NULL DEFAULT NULL COMMENT '年份',
  `quarter_period` int NULL DEFAULT NULL COMMENT '季度（1-4）',
  `growth_rate` decimal(10, 4) NULL DEFAULT NULL COMMENT '季度增长率（百分比，如0.05表示5%）',
  `statistical_date` date NULL DEFAULT NULL COMMENT '统计日期',
  `data_source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '数据来源',
  `remark` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '备注',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '规格编号',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_industry_quarter`(`industry_code`, `quarter_year`, `quarter_period`) USING BTREE,
  INDEX `idx_product_category`(`product_category`) USING BTREE,
  INDEX `idx_statistical_date`(`statistical_date`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '行业趋势统计数据表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for join_type
-- ----------------------------
DROP TABLE IF EXISTS `join_type`;
CREATE TABLE `join_type`  (
  `join_type_id` bigint NOT NULL AUTO_INCREMENT COMMENT '加盟类型ID',
  `join_type` tinyint NULL DEFAULT NULL COMMENT '加盟类型（1店铺 2配送员 3安装员）',
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '名称',
  `store_type` tinyint NULL DEFAULT NULL COMMENT '店铺类型（1商家 2门店(附近店) 3厂家 4销售商）',
  `join_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '加盟费',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  PRIMARY KEY (`join_type_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '加盟类型表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for like_record
-- ----------------------------
DROP TABLE IF EXISTS `like_record`;
CREATE TABLE `like_record`  (
  `like_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '点赞记录id',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '被点赞ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户ID',
  `account_head` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户头像',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户昵称',
  `like_type` tinyint NOT NULL DEFAULT 1 COMMENT '点赞类型（1动态 2资讯评论）',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`like_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '点赞记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for live_stream
-- ----------------------------
DROP TABLE IF EXISTS `live_stream`;
CREATE TABLE `live_stream`  (
  `live_stream_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '直播ID',
  `live_type` tinyint NULL DEFAULT 0 COMMENT '直播类型（1:视频直播 2:语音直播）',
  `voice_live_type` tinyint NULL DEFAULT 0 COMMENT '语音直播类型（1:聊天室 2:电台 3:KTV）',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `live_title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播标题',
  `live_cover_picture` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播封面图',
  `live_duration` bigint NULL DEFAULT 0 COMMENT '直播时长（毫秒）',
  `live_start_time` datetime NULL DEFAULT NULL COMMENT '直播开始时间',
  `live_end_time` datetime NULL DEFAULT NULL COMMENT '直播结束时间',
  `live_status` tinyint NULL DEFAULT 0 COMMENT '直播状态(0:未开始 1:已开始 2:已结束)',
  `exposure_duration` bigint NULL DEFAULT 0 COMMENT '曝光时长（毫秒）',
  `exposure_end_time` datetime NULL DEFAULT NULL COMMENT '曝光结束时间',
  `exposure_integral` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '曝光积分数',
  `live_pay_status` tinyint NULL DEFAULT 0 COMMENT '直播付费状态（0:不需要支付 1:需要支付）',
  `pay_integral` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '付费积分数',
  `gift_number` int NULL DEFAULT 0 COMMENT '礼物数',
  `views_number` int NULL DEFAULT 0 COMMENT '观看人数',
  `add_follower_number` int NULL DEFAULT 0 COMMENT '新增关注数',
  `rewards_number` int NULL DEFAULT 0 COMMENT '打赏人数',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `room_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '房间号',
  `address` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '所在地址',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址纬度',
  `province_code` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '城市id',
  `chat_background` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '语音背景图',
  `like_number` int NULL DEFAULT 0 COMMENT '点赞数',
  `cdn_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'CDN转推URL，只支持rtmp链接',
  `good_type` tinyint NULL DEFAULT 0 COMMENT '挂载商品类型（1商城商品 2服务）',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主键id',
  PRIMARY KEY (`live_stream_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '直播列表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for live_stream_account
-- ----------------------------
DROP TABLE IF EXISTS `live_stream_account`;
CREATE TABLE `live_stream_account`  (
  `live_stream_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '直播间用户ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `live_stream_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播ID',
  `room_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '房间号',
  `enter_time` datetime NULL DEFAULT NULL COMMENT '进入时间',
  `leave_time` datetime NULL DEFAULT NULL COMMENT '离开时间',
  `account_role` tinyint NULL DEFAULT 0 COMMENT '用户角色类型（20:主播  21:观众）',
  `terminal_type` tinyint NULL DEFAULT NULL COMMENT '终端类型(1:Windows 端 2:Android 端 3:iOS 端 4:Linux 端  100:其他)',
  `account_type` tinyint NULL DEFAULT 0 COMMENT '用户类型(1:webrtc 2:小程序 3：Native SDK)',
  `enter_reason` tinyint NULL DEFAULT 0 COMMENT '进房原因 1：正常进房 2：切换网络 3：超时重试 4：跨房连麦进房',
  `leave_reason` tinyint NULL DEFAULT 0 COMMENT '进房原因 1：正常退房 2：超时离开 3：房间用户被移出 4：取消连麦退房 5:强杀',
  `account_status` tinyint NULL DEFAULT 0 COMMENT '用户状态（1：在直播间 2：已离开直播间）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `link_status` tinyint NULL DEFAULT 0 COMMENT '连麦状态（0:未连麦 1:已连麦）',
  `microphone_status` tinyint NULL DEFAULT 0 COMMENT '麦克风状态(0:未开启 1：已开启)',
  `camera_status` tinyint NULL DEFAULT 0 COMMENT '摄像头状态(0:未开启 1：已开启)',
  `comment_num` int NULL DEFAULT 0 COMMENT '评论数量',
  `goods_click_num` int NULL DEFAULT 0 COMMENT '商品点击数量',
  `order_num` int NULL DEFAULT 0 COMMENT '下单数',
  PRIMARY KEY (`live_stream_account_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '直播间用户' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for live_stream_data
-- ----------------------------
DROP TABLE IF EXISTS `live_stream_data`;
CREATE TABLE `live_stream_data`  (
  `live_stream_data_id` bigint NOT NULL AUTO_INCREMENT COMMENT '直播数据记录ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户ID',
  `date_type` tinyint NULL DEFAULT 1 COMMENT '数据类型 1曝光记录 2进房记录 3停留记录',
  `day` date NULL DEFAULT NULL COMMENT '日期',
  `live_stream_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `fans_status` tinyint NULL DEFAULT 0 COMMENT '粉丝状态 0否 1是',
  PRIMARY KEY (`live_stream_data_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '直播数据记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for manage_data
-- ----------------------------
DROP TABLE IF EXISTS `manage_data`;
CREATE TABLE `manage_data`  (
  `manage_data_id` bigint NOT NULL AUTO_INCREMENT COMMENT '经营数据记录ID',
  `exposure_location` tinyint NULL DEFAULT 1 COMMENT '曝光位置1',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户ID',
  `date_type` tinyint NULL DEFAULT 1 COMMENT '数据类型 1曝光记录 2入店记录 3下单',
  `day` date NULL DEFAULT NULL COMMENT '日期',
  PRIMARY KEY (`manage_data_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 356 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '经营数据记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for message_record
-- ----------------------------
DROP TABLE IF EXISTS `message_record`;
CREATE TABLE `message_record`  (
  `message_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '消息记录ID',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `model_status` tinyint NULL DEFAULT NULL COMMENT '消息类型（1系统消息 2审核消息）',
  `title` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标题',
  `brief` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '消息内容',
  `Jump_type` tinyint NULL DEFAULT NULL COMMENT '跳转类型0:不跳转 1:详情 2:采购收票 3: 费用收票  5：采购付款 6：费用付款  7：合同 8：采购  9：销售 10:流转表 11:销售合同收款 12流转表收款 13:销售合同开票 14流转表开票 15oa',
  `model_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '跳转的ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '读取状态（0未读 1已读）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '是否删除（0：否 1：是）',
  `operate_user_id` bigint NULL DEFAULT NULL COMMENT '操作用户ID',
  `examine_module_id` bigint NULL DEFAULT NULL COMMENT '审批类型ID  1：补卡申请 2：报销 3：用印申请 4：请假 5：请款 6：请款冲抵 7：项目结算 8：其他',
  `operation_status` tinyint NULL DEFAULT NULL COMMENT '操作状态（1：我发起的  2：我审核的  3：抄送我的）',
  `expense_type` tinyint NULL DEFAULT 0 COMMENT '报销类型（1：差旅费 2：招待费 3:其他 ）',
  `pending_status` tinyint NULL DEFAULT 0 COMMENT '是否需要处理',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  PRIMARY KEY (`message_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '消息记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for message_remind
-- ----------------------------
DROP TABLE IF EXISTS `message_remind`;
CREATE TABLE `message_remind`  (
  `message_remind_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '消息提醒表',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `model_status` tinyint NULL DEFAULT 0 COMMENT '消息类型（1:系统消息,2:订单消息）',
  `message_title` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '消息标题',
  `message_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '消息内容',
  `cover_image` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '缩略图',
  `goods_name` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '商品名称',
  `jump_type` tinyint NULL DEFAULT 0 COMMENT '跳转类型(0:不跳转,1:用户服务订单,2:积分订单,3:师傅服务订单)',
  `model_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '跳转ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '读取状态（0未读 1已读）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '删除状态（0未1已）',
  PRIMARY KEY (`message_remind_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '消息提醒表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for new_project_collect
-- ----------------------------
DROP TABLE IF EXISTS `new_project_collect`;
CREATE TABLE `new_project_collect`  (
  `new_project_collect_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '综合情况ID',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `win_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '执行单位(创建项目的人)',
  `money_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '销售合同金额',
  `paid_money_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '销售回款金额',
  `unpaid_money_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '销售未回款金额',
  `paid_invoice_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '销售已开票金额',
  `unpaid_invoice_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '销售未开票金额',
  `sign_time` datetime NULL DEFAULT NULL COMMENT '销售签约时间',
  `total_cost_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '总和成本=未流转采购成本/流转表最新采购成本+执行情况中的核算金额合计',
  `tax_unit_total_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '未流转采购成本/流转表最新采购成本',
  `other_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '执行情况中的核算金额合计',
  `purchase_paid_money_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '采购应付款',
  `purchase_paid_invoice_total` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '采购应收票',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `win_id` bigint NULL DEFAULT NULL COMMENT '执行单位ID',
  PRIMARY KEY (`new_project_collect_id`) USING BTREE,
  INDEX `new_project_library_index`(`new_project_library_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '综合情况表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for new_project_library
-- ----------------------------
DROP TABLE IF EXISTS `new_project_library`;
CREATE TABLE `new_project_library`  (
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `region_id` bigint NULL DEFAULT NULL COMMENT '区域ID',
  `industry_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '行业类型（electricity电力 transportation交通）',
  `project_leader` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目负责人',
  `purchase_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '预算采购金额',
  `sale_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '预算销售金额',
  `estimated_cost` decimal(10, 2) NULL DEFAULT NULL COMMENT '预算费用',
  `cost` decimal(10, 2) NULL DEFAULT NULL COMMENT '成本',
  `profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '利润',
  `del_flag` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `region` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区域',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`new_project_library_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '项目库表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for oa_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `oa_copy_record`;
CREATE TABLE `oa_copy_record`  (
  `oa_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'OA抄送记录',
  `examine_initiate_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`oa_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'OA抄送记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for oa_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `oa_examine_flow`;
CREATE TABLE `oa_examine_flow`  (
  `oa_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'OA审批流程ID',
  `examine_initiate_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`oa_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'OA审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for options
-- ----------------------------
DROP TABLE IF EXISTS `options`;
CREATE TABLE `options`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `option_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '选项键',
  `type` int NULL DEFAULT 0 COMMENT '预留字段',
  `option_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '选项值',
  `create_date` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_date` datetime NULL DEFAULT NULL COMMENT '修改时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 17 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '附件设置' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for order_address
-- ----------------------------
DROP TABLE IF EXISTS `order_address`;
CREATE TABLE `order_address`  (
  `order_address_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '订单地址',
  `service_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单ID',
  `address_type` tinyint NULL DEFAULT 0 COMMENT '地址类型(1=起点,2=终点)',
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系人',
  `contact_mobile` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '联系电话',
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省编码',
  `province` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市编码',
  `city` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县编码',
  `county` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '地址',
  `address_details` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '地址详情',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '纬度',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  PRIMARY KEY (`order_address_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单地址' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for order_black_record
-- ----------------------------
DROP TABLE IF EXISTS `order_black_record`;
CREATE TABLE `order_black_record`  (
  `order_black_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '订单拉黑ID',
  `service_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单ID',
  `work_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅用户ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅认证ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  PRIMARY KEY (`order_black_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单拉黑' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for order_complaint
-- ----------------------------
DROP TABLE IF EXISTS `order_complaint`;
CREATE TABLE `order_complaint`  (
  `order_complaint_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '订单投诉ID',
  `service_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `work_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅用户ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅认证ID',
  `complaint_status` tinyint NULL DEFAULT 0 COMMENT '投诉状态(0=待审核,1=已通过,2=已拒绝)',
  `complaint_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '投诉原因',
  `complaint_reason_details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '投诉原因详情',
  `complaint_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '投诉原因图片',
  `platform_reply` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '平台回复',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `work_reply` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅回复',
  `appeal_status` tinyint NULL DEFAULT 0 COMMENT '申诉状态(0=未申诉,1=已申诉)',
  `appeal_reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '申诉原因',
  `appeal_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '申诉图片',
  `reply_status` tinyint NULL DEFAULT 0 COMMENT '回复状态(0=未回复,1=已回复)',
  `account_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户名称',
  `account_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户头像',
  PRIMARY KEY (`order_complaint_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单投诉' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for order_evaluate
-- ----------------------------
DROP TABLE IF EXISTS `order_evaluate`;
CREATE TABLE `order_evaluate`  (
  `order_evaluate_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '订单评价ID',
  `service_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `work_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅用户ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅认证ID',
  `service_project_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务项目ID',
  `evaluate_star` tinyint NULL DEFAULT 0 COMMENT '评价星级',
  `evaluate_label` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '评价标签',
  `evaluate_level` tinyint NULL DEFAULT 0 COMMENT '评价等级（1差评(1/2/3星) 2中评(4星) 3好评(5星)）',
  `evaluate_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '评价内容',
  `evaluate_pic` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '评价图片',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `reply_status` tinyint NULL DEFAULT 0 COMMENT '回复状态(0=未回复,1=已回复)',
  `work_reply` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅回复',
  `account_head` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '头像',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '昵称',
  PRIMARY KEY (`order_evaluate_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单评价' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for order_price
-- ----------------------------
DROP TABLE IF EXISTS `order_price`;
CREATE TABLE `order_price`  (
  `order_price_id` bigint NOT NULL AUTO_INCREMENT COMMENT '商品价格范围id',
  `min_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '最小价格',
  `max_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '最大价格',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '价格范围',
  PRIMARY KEY (`order_price_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '订单价格表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for order_time
-- ----------------------------
DROP TABLE IF EXISTS `order_time`;
CREATE TABLE `order_time`  (
  `order_time_id` bigint NOT NULL AUTO_INCREMENT COMMENT '订单时间ID',
  `name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '时段名称',
  `start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '结束时间',
  PRIMARY KEY (`order_time_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 8 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '订单时间表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for out_bound
-- ----------------------------
DROP TABLE IF EXISTS `out_bound`;
CREATE TABLE `out_bound`  (
  `out_bound_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '出库记录id',
  `purchase_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购编号',
  `in_bound_status` tinyint NULL DEFAULT 0 COMMENT '入库状态(0:待出库 1：已出库 )',
  `sales_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售记录ID',
  `leave_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单据编码',
  `stock_num` int NULL DEFAULT NULL COMMENT '库存数量',
  `leave_date` datetime NULL DEFAULT NULL COMMENT '出库日期',
  `signature_date` datetime NULL DEFAULT NULL COMMENT '签收日期',
  `logistics_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流方式',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态 0：显示 1：隐藏',
  `sort_num` bigint NULL DEFAULT 1 COMMENT '排序，数字越小越靠前',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `contract_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编码',
  `out_bound_detail_type` tinyint NULL DEFAULT 1 COMMENT '出库类型(1:销售出库 2：退换货出库)',
  `delivery_person` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出库人',
  `delivery_person_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出库人id',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  PRIMARY KEY (`out_bound_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '出库记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for out_bound_detail
-- ----------------------------
DROP TABLE IF EXISTS `out_bound_detail`;
CREATE TABLE `out_bound_detail`  (
  `out_bound_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '出库记录详情id',
  `out_bound_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出库记录id',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类别',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态 0：显示 1：隐藏',
  `sort_num` bigint NULL DEFAULT 1 COMMENT '排序，数字越小越靠前',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `purchase_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购编号',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存数量',
  `stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '库存表id',
  `sales_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售详情id（实际发货）',
  PRIMARY KEY (`out_bound_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '出库记录详情' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for pay_config
-- ----------------------------
DROP TABLE IF EXISTS `pay_config`;
CREATE TABLE `pay_config`  (
  `pay_config_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '支付配置ID',
  `application_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '应用名字',
  `pay_platform` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '支付平台（alipay支付宝，wx微信）',
  `pay_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '支付方式（alipay_app=支付宝APP支付，\r\nalipay_pc=支付宝pc支付，alipay_wap=支付宝wap支付，JSAPI=微信公众号小程序支付，MWEB=微信H5支付，NATIVE=微信Native支付，APP=微信APP支付\r\n）',
  `app_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'APP_ID',
  `app_secret` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT 'APP_SECRET',
  `private_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '支付宝应用私钥',
  `notify_url` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '支付回调地址',
  `cert_path` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '支付宝应用公钥证书路径（appCertPublicKey_2021.crt）',
  `public_cert_path` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '支付宝公钥证书路径（alipayCertPublicKey_RSA2.crt）',
  `root_cert_path` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '支付宝根证书路径（alipayRootCert.crt）',
  `mch_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信支付商户号',
  `mch_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '微信支付商户秘钥',
  `sub_app_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务商模式下的子商户公众账号ID',
  `sub_mch_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '服务商模式下的子商户号',
  `key_path` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '微信支付证书的位置',
  `apiclient_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '微信支付apiclient_key.pem证书文件（暂时不用）',
  `apiclient_cert` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '微信支付apiclient_cert.pem证书文件（暂时不用）',
  `api_v3_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT 'apiV3秘钥值（暂时不用）',
  `cert_serial_no` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT 'apiV3证书序列号值（暂时不用）',
  `start_status` tinyint NOT NULL DEFAULT 0 COMMENT '是否启用（1启用 0关闭）',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `public_key_path` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信支付pub key.pem证书文件地址',
  `public_key_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信支付key_id',
  PRIMARY KEY (`pay_config_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '支付配置2.0版' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for payment
-- ----------------------------
DROP TABLE IF EXISTS `payment`;
CREATE TABLE `payment`  (
  `payment_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '付款id',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主键id',
  `pay_price` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '本次付款金额',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '明细备注',
  `operator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '操作人',
  `voucher` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '付款凭证',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `pay_date` datetime NULL DEFAULT NULL COMMENT '付款日期',
  `open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '承兑银行',
  `proceeds_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '收款行',
  `draft_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出票日期',
  `expire_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '到期日期',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `pay_type` tinyint NULL DEFAULT 1 COMMENT '付款类型 1采购付款 2费用付款',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `bank_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联行号',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  PRIMARY KEY (`payment_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '付款表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for payment_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `payment_copy_record`;
CREATE TABLE `payment_copy_record`  (
  `payment_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '付款抄送记录',
  `payment_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`payment_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '付款抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for payment_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `payment_examine_flow`;
CREATE TABLE `payment_examine_flow`  (
  `payment_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '付款审批流程ID',
  `payment_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`payment_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '付款审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for payment_invoice
-- ----------------------------
DROP TABLE IF EXISTS `payment_invoice`;
CREATE TABLE `payment_invoice`  (
  `payment_invoice_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '开票ID',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主键id',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行',
  `open_bank_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行账号账号',
  `duty_paragraph` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '税号',
  `contact_person` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `remarks` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `invoice_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '开票金额',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `invoice_status` tinyint NULL DEFAULT NULL COMMENT '开票状态(0:未开票 1：已开票)',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `operator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '操作人',
  `pay_type` tinyint NULL DEFAULT 1 COMMENT '付款类型 1销售收款 2项目流转收款',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `attachment` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '附件',
  `detail_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  PRIMARY KEY (`payment_invoice_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '开票表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for payment_invoice_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `payment_invoice_copy_record`;
CREATE TABLE `payment_invoice_copy_record`  (
  `payment_invoice_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '开票抄送记录',
  `payment_invoice_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`payment_invoice_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '开票抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for payment_invoice_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `payment_invoice_examine_flow`;
CREATE TABLE `payment_invoice_examine_flow`  (
  `payment_invoice_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '开票审批流程ID',
  `payment_invoice_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`payment_invoice_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '开票审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for proceeds
-- ----------------------------
DROP TABLE IF EXISTS `proceeds`;
CREATE TABLE `proceeds`  (
  `proceeds_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收款id',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主键id',
  `pay_price` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '本次回款金额',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '明细备注',
  `operator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '操作人',
  `voucher` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '收款凭证',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `pay_date` datetime NULL DEFAULT NULL COMMENT '收款日期',
  `open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '承兑银行',
  `proceeds_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '收款行',
  `draft_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '出票日期',
  `expire_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '到期日期',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `pay_type` tinyint NULL DEFAULT 1 COMMENT '付款类型 1销售收款 2项目流转收款',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  PRIMARY KEY (`proceeds_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收款表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for proceeds_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `proceeds_copy_record`;
CREATE TABLE `proceeds_copy_record`  (
  `proceeds_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收款抄送记录',
  `proceeds_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`proceeds_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收款抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for proceeds_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `proceeds_examine_flow`;
CREATE TABLE `proceeds_examine_flow`  (
  `proceeds_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收款审批流程ID',
  `proceeds_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`proceeds_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收款审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for proceeds_invoice
-- ----------------------------
DROP TABLE IF EXISTS `proceeds_invoice`;
CREATE TABLE `proceeds_invoice`  (
  `proceeds_invoice_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收票id',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主键id',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '明细备注',
  `operator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '操作人',
  `voucher` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '付款凭证',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `invoice_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '开票金额',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `pay_type` tinyint NULL DEFAULT 1 COMMENT '付款类型 1采购收票 2费用收票',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `attachment` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '附件',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  PRIMARY KEY (`proceeds_invoice_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收票表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for proceeds_invoice_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `proceeds_invoice_copy_record`;
CREATE TABLE `proceeds_invoice_copy_record`  (
  `proceeds_invoice_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收票抄送记录',
  `proceeds_invoice_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`proceeds_invoice_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收票抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for proceeds_invoice_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `proceeds_invoice_examine_flow`;
CREATE TABLE `proceeds_invoice_examine_flow`  (
  `proceeds_invoice_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '收票审批流程ID',
  `proceeds_invoice_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`proceeds_invoice_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '收票审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project
-- ----------------------------
DROP TABLE IF EXISTS `project`;
CREATE TABLE `project`  (
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '项目名称',
  `client_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户单位',
  `year` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `region_id` bigint NOT NULL COMMENT '区域ID',
  `executing_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '执行单位',
  `profit` decimal(20, 2) NOT NULL DEFAULT 0.00 COMMENT '利润',
  `project_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '项目类型（ecommerce电商 supplies物资 services服务）',
  `industry_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '行业类型（electricity电力 transportation交通）',
  `project_leader` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '项目负责人',
  `transfer_status` tinyint(1) NOT NULL DEFAULT 0 COMMENT '流转状态（0否 1是）',
  `audit_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'inReview' COMMENT '审核状态（inReview审核中 passed已通过 rejection已拒绝）',
  `project_progress` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'planning' COMMENT '项目进度（planning立项 in_progress开工 completed竣工 closed完工）',
  `winning_bid_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '中标单位',
  `procurement_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购单位',
  `supplier` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商',
  `contract_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '合同内容',
  `procurement_unit_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '采购单位金额',
  `supplier_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '供应商金额',
  `service_fee` decimal(20, 2) NULL DEFAULT NULL COMMENT '服务费',
  `other_expenses` decimal(20, 2) NULL DEFAULT NULL COMMENT '其他费用',
  `estimated_profit` decimal(20, 2) NULL DEFAULT NULL COMMENT '预估利润',
  `reserved_field1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段1',
  `reserved_field2` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段2',
  `reserved_field3` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段3',
  `reserved_field4` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段4',
  `reserved_field5` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段5',
  `reserved_field6` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段6',
  `product_info_and_remarks` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品信息及其他备注',
  `contract_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '合同金额',
  `recovery_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '回款金额',
  `receivable_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '应收账款',
  `recovery_rate` decimal(5, 2) NULL DEFAULT NULL COMMENT '回款率',
  `purchase_invoices_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '开票金额',
  `uninvoiced_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '未开票金额',
  `total_cost` decimal(20, 2) NULL DEFAULT NULL COMMENT '综合成本',
  `payable_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '应付账款',
  `receivable_invoice` decimal(20, 2) NULL DEFAULT NULL COMMENT '应收发票',
  `profit_margin` decimal(5, 2) NULL DEFAULT NULL COMMENT '利润率',
  `bonus_calculation` decimal(20, 2) NULL DEFAULT NULL COMMENT '奖金核算',
  `execute_purchase_actual_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '执行采购实际金额合计',
  `execute_purchase_calculation_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '执行采购核算金额合计',
  `execute_purchase_payable_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '执行采购应付账款合计',
  `execute_purchase_unbilled_actual_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '执行采购欠票实际金额合计',
  `execute_purchase_receipt_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '执行采购收票金额合计',
  `execute_purchase_payment_receipt_amount` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '执行采购付款收票金额合计',
  `others` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '其他事项',
  `board_id` bigint NULL DEFAULT NULL COMMENT '董事会ID',
  `finance_id` bigint NULL DEFAULT NULL COMMENT '财务部ID',
  `general_manager_id` bigint NULL DEFAULT NULL COMMENT '总经办ID',
  `enterprise_management_id` bigint NULL DEFAULT NULL COMMENT '企管部ID',
  `preparer_id` bigint NULL DEFAULT NULL COMMENT '制表人ID',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `reject_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  PRIMARY KEY (`project_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '项目表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_execution
-- ----------------------------
DROP TABLE IF EXISTS `project_execution`;
CREATE TABLE `project_execution`  (
  `execution_id` bigint NOT NULL COMMENT '执行ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `execution_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '执行类型（brokerage_fee居间服务费 bid_service_fee中标服务费 communication_fee通讯费 installation_fee安装费 technical_service_fee技术服务费 platform_fee平台手续费 other_fee其他费用 performance_deposit履约保证金 provisional_sum暂定金 reimbursement_fee报销费用 public_expense公摊费）',
  `unit_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位名称',
  `actual_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '实际金额',
  `tax_rate` decimal(5, 2) NULL DEFAULT NULL COMMENT '税率（例如13.00表示13%）',
  `calculated_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '核算金额',
  `payable_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '应付账款',
  `uninvoiced_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '欠票金额',
  `received_invoice_total` decimal(20, 2) NULL DEFAULT NULL COMMENT '收票合计',
  `payment_total` decimal(20, 2) NULL DEFAULT NULL COMMENT '付款合计',
  `sort_num` int NULL DEFAULT NULL COMMENT '排序号',
  `can_deleted` tinyint NULL DEFAULT 0 COMMENT '是否可删除（前端用）',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`execution_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '项目执行表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_execution_invoice
-- ----------------------------
DROP TABLE IF EXISTS `project_execution_invoice`;
CREATE TABLE `project_execution_invoice`  (
  `invoice_id` bigint NOT NULL COMMENT '发票ID',
  `execution_id` bigint NOT NULL COMMENT '执行ID',
  `invoice_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '收票金额',
  `invoice_date` datetime NULL DEFAULT NULL COMMENT '收票时间',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `project_id` bigint NULL DEFAULT NULL COMMENT '项目ID',
  PRIMARY KEY (`invoice_id`) USING BTREE,
  INDEX `idx_pei_project_id`(`project_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '执行发票表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_execution_payment
-- ----------------------------
DROP TABLE IF EXISTS `project_execution_payment`;
CREATE TABLE `project_execution_payment`  (
  `payment_id` bigint NOT NULL COMMENT '付款ID',
  `execution_id` bigint NOT NULL COMMENT '执行ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `payment_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '付款金额',
  `payment_time` datetime NULL DEFAULT NULL COMMENT '付款时间',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`payment_id`) USING BTREE,
  INDEX `idx_pep_project_id`(`project_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '执行付款表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_flow
-- ----------------------------
DROP TABLE IF EXISTS `project_flow`;
CREATE TABLE `project_flow`  (
  `flow_id` bigint NOT NULL COMMENT '流转ID',
  `purchases_id` bigint NOT NULL COMMENT '采销ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '项目流转表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_flow_unit
-- ----------------------------
DROP TABLE IF EXISTS `project_flow_unit`;
CREATE TABLE `project_flow_unit`  (
  `flow_unit_id` bigint NOT NULL COMMENT '流转单位ID',
  `purchases_id` bigint NOT NULL COMMENT '采销ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `flow_id` bigint NOT NULL COMMENT '流转ID',
  `unit_nature` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位性质',
  `unit_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位名称',
  `contract_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '合同金额',
  `received_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '已回款金额小计',
  `output_invoice_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '销项票小计',
  `remarks` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '备注',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`flow_unit_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '流转单位表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_flow_unit_output_invoice
-- ----------------------------
DROP TABLE IF EXISTS `project_flow_unit_output_invoice`;
CREATE TABLE `project_flow_unit_output_invoice`  (
  `output_invoice_id` bigint NOT NULL COMMENT '流转单位销项票ID',
  `flow_id` bigint NOT NULL COMMENT '流转ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `purchases_id` bigint NOT NULL COMMENT '采销ID',
  `flow_unit_id` bigint NOT NULL COMMENT '流转单位ID',
  `output_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '销项票金额',
  `output_date` date NULL DEFAULT NULL COMMENT '销项票时间',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`output_invoice_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '流转销项票表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_flow_unit_payment
-- ----------------------------
DROP TABLE IF EXISTS `project_flow_unit_payment`;
CREATE TABLE `project_flow_unit_payment`  (
  `flow_payment_id` bigint NOT NULL COMMENT '流转单位回款ID',
  `flow_id` bigint NOT NULL COMMENT '流转ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `purchases_id` bigint NOT NULL COMMENT '采销ID',
  `flow_unit_id` bigint NOT NULL COMMENT '流转单位ID',
  `received_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '已回款金额',
  `received_date` date NULL DEFAULT NULL COMMENT '已回款时间',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`flow_payment_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '流转回款表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_purchase_invoices
-- ----------------------------
DROP TABLE IF EXISTS `project_purchase_invoices`;
CREATE TABLE `project_purchase_invoices`  (
  `invoice_id` bigint NOT NULL COMMENT '发票唯一标识',
  `purchases_id` bigint NOT NULL COMMENT '关联生产采销ID',
  `project_id` bigint NOT NULL COMMENT '关联项目ID',
  `invoice_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '开票金额',
  `invoice_date` date NULL DEFAULT NULL COMMENT '开票日期',
  `payment_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '收款金额',
  `payment_date` date NULL DEFAULT NULL COMMENT '收款日期',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`invoice_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采销发票表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_purchase_suppliers
-- ----------------------------
DROP TABLE IF EXISTS `project_purchase_suppliers`;
CREATE TABLE `project_purchase_suppliers`  (
  `supplier_id` bigint NOT NULL COMMENT '采销供应商ID',
  `purchases_id` bigint NULL DEFAULT NULL COMMENT '采销ID',
  `project_id` bigint NULL DEFAULT NULL COMMENT '项目ID',
  `supplier_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `purchase_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '采购金额',
  `purchase_date` date NULL DEFAULT NULL COMMENT '采购日期',
  `tax_rate` decimal(5, 2) NULL DEFAULT NULL COMMENT '税率',
  `invoice_subtotal` decimal(20, 2) NULL DEFAULT NULL COMMENT '收票小计金额',
  `payment_subtotal` decimal(20, 2) NULL DEFAULT NULL COMMENT '付款小计金额',
  `reserved_field1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段1',
  `del_flag` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NULL DEFAULT NULL COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`supplier_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采销供应商表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_purchases
-- ----------------------------
DROP TABLE IF EXISTS `project_purchases`;
CREATE TABLE `project_purchases`  (
  `purchases_id` bigint NOT NULL COMMENT '采销ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `customer_company` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户单位',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率',
  `contract_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '合同金额',
  `contract_date` date NULL DEFAULT NULL COMMENT '合同签订日期',
  `is_circulated` tinyint NOT NULL DEFAULT 0 COMMENT '是否流转（0否 1是）',
  `invoice_subtotal` decimal(20, 2) NULL DEFAULT NULL COMMENT '开票小计金额',
  `payment_subtotal` decimal(20, 2) NULL DEFAULT NULL COMMENT '收款小计金额',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `reserved_field1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '保留字段1',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`purchases_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '项目采销表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for project_purchases_supplier_invoices
-- ----------------------------
DROP TABLE IF EXISTS `project_purchases_supplier_invoices`;
CREATE TABLE `project_purchases_supplier_invoices`  (
  `invoice_id` bigint NOT NULL COMMENT '供应商发票ID',
  `purchases_id` bigint NOT NULL COMMENT '采销ID',
  `project_id` bigint NOT NULL COMMENT '项目ID',
  `supplier_id` bigint NOT NULL COMMENT '供应商ID',
  `received_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '收票金额',
  `received_date` date NULL DEFAULT NULL COMMENT '收票日期',
  `payment_amount` decimal(20, 2) NULL DEFAULT NULL COMMENT '付款金额',
  `payment_date` date NULL DEFAULT NULL COMMENT '付款日期',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_by` bigint NOT NULL COMMENT '创建者',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`invoice_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '供应商发票表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for promoter
-- ----------------------------
DROP TABLE IF EXISTS `promoter`;
CREATE TABLE `promoter`  (
  `promoter_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '推广员ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `real_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '姓名',
  `sex` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '性别',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '手机号',
  `id_card_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证号',
  `id_card_front_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证人像面照片',
  `id_card_back_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证国徽面照片',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '所在地区',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  `total_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '总收益',
  `remaining_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '余额',
  `withdrawal_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `frozen_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '冻结金额',
  `wait_entry_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '待入账金额',
  `edit_audit_status` tinyint NULL DEFAULT -1 COMMENT '资料编辑审核状态（-1未提交 0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '资料编辑审核拒绝原因',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺分类ID',
  `city_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市ID',
  `province_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省ID',
  `county_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县ID',
  `town_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇ID',
  PRIMARY KEY (`promoter_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '推广员表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for promoter_apply
-- ----------------------------
DROP TABLE IF EXISTS `promoter_apply`;
CREATE TABLE `promoter_apply`  (
  `promoter_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '推广员申请ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `agent_type` tinyint NULL DEFAULT NULL COMMENT '代理商类型（1市级代理商 2区县级代理商 3市级行业代理商 4区县级行业代理商）',
  `real_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '姓名',
  `sex` varchar(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '性别',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '手机号',
  `id_card_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证号',
  `id_card_front_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证人像面照片',
  `id_card_back_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证国徽面照片',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `audit_status` tinyint NULL DEFAULT -1 COMMENT '审核状态（-1未支付 0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '所在地区',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺分类ID',
  `city_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市ID',
  `province_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '省ID',
  `county_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '区县ID',
  `town_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '街道/乡镇ID',
  PRIMARY KEY (`promoter_apply_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '推广员申请表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `purchase_copy_record`;
CREATE TABLE `purchase_copy_record`  (
  `purchase_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '采购抄送记录ID',
  `purchase_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购记录ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`purchase_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_details
-- ----------------------------
DROP TABLE IF EXISTS `purchase_details`;
CREATE TABLE `purchase_details`  (
  `purchase_details_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '采购详情ID',
  `purchase_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购记录ID',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `product_count` int NULL DEFAULT NULL COMMENT '产品数量',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类型（1：单体  2：成套）',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `no_tax_unit_price` decimal(20, 8) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_unit_price` decimal(20, 8) NULL DEFAULT NULL COMMENT '含税进价',
  `no_tax_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税总价',
  `tax_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税总价',
  `delivery_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '货期',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `data_bank_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '资料库ID',
  PRIMARY KEY (`purchase_details_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购详情' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `purchase_examine_flow`;
CREATE TABLE `purchase_examine_flow`  (
  `purchase_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '采购审批流程ID',
  `purchase_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购记录ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`purchase_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_record
-- ----------------------------
DROP TABLE IF EXISTS `purchase_record`;
CREATE TABLE `purchase_record`  (
  `purchase_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '采购记录ID',
  `purchase_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购编号',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `sign_time` datetime NULL DEFAULT NULL COMMENT '签约时间',
  `expire_time` datetime NULL DEFAULT NULL COMMENT '到期时间',
  `payment_method` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '付款方式 1先货后款 2先款后货',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '金额合计',
  `paid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已付金额合计',
  `unpaid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未付金额合计',
  `arrived_count` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '已到货数量',
  `unarrived_count` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '未到货数量',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `guarantee_ratio` decimal(10, 2) NULL DEFAULT NULL COMMENT '质保比例',
  `delivery_time` datetime NULL DEFAULT NULL COMMENT '交货时间',
  `contract_document` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '合同文件',
  `paid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已开票金额',
  `unpaid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未开票金额',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `contract_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同单位',
  `data_bank_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '资料库ID',
  `principal_people` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '负责人',
  `industry_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '行业类型（electricity电力 transportation交通）',
  `purchase_sales` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购销售关联',
  PRIMARY KEY (`purchase_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_sales
-- ----------------------------
DROP TABLE IF EXISTS `purchase_sales`;
CREATE TABLE `purchase_sales`  (
  `purchase_sales_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '采购销售关联ID',
  `purchase_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购记录ID',
  `sales_contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同id',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `purchase_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '采购金额',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `is_flow` tinyint NULL DEFAULT 0 COMMENT '销售是否流转',
  PRIMARY KEY (`purchase_sales_id`) USING BTREE,
  INDEX `sales_contract_index`(`sales_contract_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '采购销售关联表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_suggestion
-- ----------------------------
DROP TABLE IF EXISTS `purchase_suggestion`;
CREATE TABLE `purchase_suggestion`  (
  `purchase_suggestion_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '采购建议ID',
  `stock_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '库存ID',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '规格编码',
  `product_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '产品名称',
  `original_quantity` int NULL DEFAULT NULL COMMENT '原始建议量（系统计算）',
  `adjusted_quantity` int NULL DEFAULT NULL COMMENT '调整后建议量',
  `adjustment_reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '调整原因（超过±20%时必填）',
  `stock_shortage` int NULL DEFAULT NULL COMMENT '库存缺口',
  `avg_daily_sales` decimal(10, 4) NULL DEFAULT NULL COMMENT '近3月日均销量',
  `estimated_cost` decimal(10, 2) NULL DEFAULT NULL COMMENT '预计采购成本',
  `supplier_manage_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '推荐供应商ID',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '推荐供应商名称',
  `procurement_cycle` int NULL DEFAULT NULL COMMENT '采购周期（天）',
  `procurement_reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '采购理由',
  `status` int NULL DEFAULT 0 COMMENT '状态（0:待处理 1:已生成采购单 2:已取消）',
  `purchase_record_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '关联的采购单ID（生成采购单后关联）',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `del_status` bigint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`purchase_suggestion_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '采购建议表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for region
-- ----------------------------
DROP TABLE IF EXISTS `region`;
CREATE TABLE `region`  (
  `region_id` bigint NOT NULL COMMENT '区域ID',
  `region_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '名称',
  `show_status` tinyint NOT NULL DEFAULT 0 COMMENT '显示状态（0隐藏 1显示）',
  `del_flag` tinyint NOT NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`region_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '区域表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for report_stock
-- ----------------------------
DROP TABLE IF EXISTS `report_stock`;
CREATE TABLE `report_stock`  (
  `report_stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '报备库存ID',
  `report_stock_num` int NULL DEFAULT 0 COMMENT '预留数量',
  `stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '库存表id',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `classify` tinyint NULL DEFAULT 2 COMMENT '产品类别1：销售报备 2：手动添加报备',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `report_user` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '报备用户',
  PRIMARY KEY (`report_stock_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '报备库存记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for report_unbound
-- ----------------------------
DROP TABLE IF EXISTS `report_unbound`;
CREATE TABLE `report_unbound`  (
  `report_unbound_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '解除报备库存记录ID',
  `report_stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '报备库存ID',
  `unbound_num` int NULL DEFAULT NULL COMMENT '解绑的数量',
  `stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '库存表id',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `classify` tinyint NULL DEFAULT NULL COMMENT '产品类别1：销售报备 2：手动添加报备',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `user_id` bigint NULL DEFAULT NULL COMMENT '解绑用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `relieve_examine_status` tinyint NULL DEFAULT 0 COMMENT '解除审批状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `refusal_reason` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `report_user` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '报备用户',
  `unbound_user` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '解绑的用户',
  `report_user_id` bigint NULL DEFAULT NULL COMMENT '报备的用户id',
  PRIMARY KEY (`report_unbound_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '解除报备库存记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales
-- ----------------------------
DROP TABLE IF EXISTS `sales`;
CREATE TABLE `sales`  (
  `sales_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售id',
  `sales_contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同id',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '金额合计',
  `sign_time` datetime NULL DEFAULT NULL COMMENT '销售合同签约时间',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `outbound_status` tinyint NULL DEFAULT 0 COMMENT '出库状态(0:未出库  1:已出库)',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  PRIMARY KEY (`sales_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_contract
-- ----------------------------
DROP TABLE IF EXISTS `sales_contract`;
CREATE TABLE `sales_contract`  (
  `sales_contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售合同id',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `new_project_library_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目库id',
  `project_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `client_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户ID',
  `client_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '客户名称',
  `brand_detail` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '分标明细',
  `subpackage_detail` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '分包明细',
  `sign_time` datetime NULL DEFAULT NULL COMMENT '签约时间',
  `expire_time` datetime NULL DEFAULT NULL COMMENT '到期时间',
  `money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '金额合计',
  `paid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已付金额合计',
  `unpaid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未付金额合计',
  `arrived_count` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '已发货数量',
  `unarrived_count` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '未发货数量',
  `delivery_time` datetime NULL DEFAULT NULL COMMENT '交货时间',
  `guarantee_ratio` decimal(10, 2) NULL DEFAULT NULL COMMENT '质保比例',
  `payment_method` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '付款方式 1先货后款 2先款后货',
  `contract_document` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '合同文件',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '创建用户',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新用户',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `examine_status` tinyint NULL DEFAULT 0 COMMENT '审核状态( 0:未审批 1：待审批  2：审批中3：已通过 4：已驳回 5：已撤回)',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  `refusal_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `paid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已开票金额',
  `unpaid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未开票金额',
  `principal_people` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '负责人',
  `region_id` bigint NULL DEFAULT NULL COMMENT '区域ID',
  `industry_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '行业类型（electricity电力 transportation交通）',
  PRIMARY KEY (`sales_contract_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售合同' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_contract_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `sales_contract_copy_record`;
CREATE TABLE `sales_contract_copy_record`  (
  `sales_contract_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '合同抄送记录',
  `contract_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同记录ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`sales_contract_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售合同抄送表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_contract_detail
-- ----------------------------
DROP TABLE IF EXISTS `sales_contract_detail`;
CREATE TABLE `sales_contract_detail`  (
  `sales_contract_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售合同详情id',
  `sale_contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同id',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `product_count` int NULL DEFAULT NULL COMMENT '产品数量',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类型（1：单体  2：成套）',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `delivery_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '货期',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `tax_sales_price` decimal(20, 8) NULL DEFAULT NULL COMMENT '含税销售价',
  `no_tax_sales_price` decimal(20, 8) NULL DEFAULT NULL COMMENT '不含税销售价',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `no_sales_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售总价',
  `sales_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售总价',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`sales_contract_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售合同详情' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_contract_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `sales_contract_examine_flow`;
CREATE TABLE `sales_contract_examine_flow`  (
  `sales_contract_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '合同审批流程ID',
  `contract_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同记录ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `contract_examine_type` tinyint NULL DEFAULT 1 COMMENT '合同审批类型（1：生成合同 2：修改合同）',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`sales_contract_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售合同审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_copy_record
-- ----------------------------
DROP TABLE IF EXISTS `sales_copy_record`;
CREATE TABLE `sales_copy_record`  (
  `sales_copy_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售抄送记录',
  `sales_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售记录ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `copy_user_id` bigint NULL DEFAULT NULL COMMENT '抄送用户ID',
  `copy_user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者姓名',
  `copy_user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者手机号',
  `copy_user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '抄送者头像',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:否 1:删除',
  PRIMARY KEY (`sales_copy_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售抄送记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_detail
-- ----------------------------
DROP TABLE IF EXISTS `sales_detail`;
CREATE TABLE `sales_detail`  (
  `sales_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售详情id（实际发货）',
  `sales_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售id',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `product_count` int NULL DEFAULT NULL COMMENT '产品数量',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类型（1：单体  2：成套）',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `delivery_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '货期',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `purchase_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购编号',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `no_tax_unit_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税总进价',
  `tax_unit_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税总进价',
  `tax_sales_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税总销售价',
  `no_tax_sales_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税总销售价',
  `stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '库存ID',
  PRIMARY KEY (`sales_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售详情（实际发货）' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_examine_flow
-- ----------------------------
DROP TABLE IF EXISTS `sales_examine_flow`;
CREATE TABLE `sales_examine_flow`  (
  `sales_examine_flow_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售审批流程ID',
  `sales_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售记录ID',
  `examine_tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '同一批审批标识',
  `user_id` bigint NULL DEFAULT NULL COMMENT '审批用户ID',
  `examine_sequence` int NULL DEFAULT NULL COMMENT '审批顺序，正序',
  `examine_status` tinyint NULL DEFAULT 1 COMMENT '审批状态 1：未审批  2：待审批3：已通过 4：已驳回 ',
  `reject_content` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因/批准原因',
  `pics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '通过/拒绝图片，多图片逗号隔开',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者手机号',
  `user_head` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审批者头像',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '审批用户所属部门ID',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读标识 0：否 1：已读',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态0:否 1:删除',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`sales_examine_flow_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售审批流程' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_should_detail
-- ----------------------------
DROP TABLE IF EXISTS `sales_should_detail`;
CREATE TABLE `sales_should_detail`  (
  `sales_should_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售详情id（应发货）',
  `sales_contract_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同详情id',
  `sale_contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同id',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `product_count` int NULL DEFAULT NULL COMMENT '产品数量',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类型（1：单体  2：成套）',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `delivery_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '货期',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `no_tax_unit_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税总进价',
  `tax_unit_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税总进价',
  `tax_sales_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税总销售价',
  `no_tax_sales_total_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税总销售价',
  `sales_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售id',
  `sales_single_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售单id',
  PRIMARY KEY (`sales_should_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售详情（应发货）' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sales_single
-- ----------------------------
DROP TABLE IF EXISTS `sales_single`;
CREATE TABLE `sales_single`  (
  `sales_single_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '销售单id',
  `sales_contract_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同详情id',
  `sale_contract_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '销售合同id',
  `contract_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '合同编号',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `product_count` int NULL DEFAULT NULL COMMENT '产品数量',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类型（1：单体  2：成套）',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `delivery_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '货期',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `project_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目编码',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  PRIMARY KEY (`sales_single_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '销售单(待发货商品)' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for seckill_apply
-- ----------------------------
DROP TABLE IF EXISTS `seckill_apply`;
CREATE TABLE `seckill_apply`  (
  `seckill_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '秒杀申请ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '结束时间',
  `use_scope` tinyint NULL DEFAULT 0 COMMENT '适用范围（0不限 1指定商品）',
  `discount` decimal(10, 2) NULL DEFAULT NULL COMMENT '秒杀折扣（%）',
  `limit_num` int NULL DEFAULT NULL COMMENT '限购数量',
  `goods_num` int NULL DEFAULT NULL COMMENT '商品数量',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `store_goods_id` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `goods_name` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `seckill_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀时段id',
  PRIMARY KEY (`seckill_apply_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '秒杀申请表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for seckill_apply_detail
-- ----------------------------
DROP TABLE IF EXISTS `seckill_apply_detail`;
CREATE TABLE `seckill_apply_detail`  (
  `seckill_apply_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '秒杀申请明细ID',
  `seckill_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀申请ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `goods_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `spec_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格名称',
  `thumb` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '缩略图',
  `market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品价格',
  `seckill_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '秒杀价格',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存',
  `goods_num` int NULL DEFAULT 0 COMMENT '商品数量',
  `start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '结束时间',
  PRIMARY KEY (`seckill_apply_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '秒杀申请明细表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for seckill_goods_time
-- ----------------------------
DROP TABLE IF EXISTS `seckill_goods_time`;
CREATE TABLE `seckill_goods_time`  (
  `seckill_goods_time_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品时段ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀商品ID',
  `start_time` datetime NULL DEFAULT NULL COMMENT '秒杀开始时间',
  `end_time` datetime NULL DEFAULT NULL COMMENT '秒杀结束时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `discount` decimal(10, 2) NULL DEFAULT NULL COMMENT '秒杀折扣（%）',
  `limit_num` int NULL DEFAULT 0 COMMENT '限购数量',
  `goods_num` int NULL DEFAULT 0 COMMENT '商品数量',
  `surplus_goods_num` int NULL DEFAULT 0 COMMENT '剩余商品数量',
  `seckill_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀申请ID',
  PRIMARY KEY (`seckill_goods_time_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '秒杀商品时段中间表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for seckill_time
-- ----------------------------
DROP TABLE IF EXISTS `seckill_time`;
CREATE TABLE `seckill_time`  (
  `seckill_time_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '秒杀时间ID',
  `start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '结束时间',
  PRIMARY KEY (`seckill_time_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '秒杀时间' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for serve_negotiated_price
-- ----------------------------
DROP TABLE IF EXISTS `serve_negotiated_price`;
CREATE TABLE `serve_negotiated_price`  (
  `serve_negotiated_price_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '议价记录ID',
  `serve_quoted_price_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单报价ID',
  `negotiated_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '议价金额',
  `negotiated_status` tinyint NULL DEFAULT 1 COMMENT '议价状态（1：同意议价 2：拒绝议价）',
  `negotiated_time` datetime NULL DEFAULT NULL COMMENT '议价时间',
  `negotiated_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '议价理由',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  PRIMARY KEY (`serve_negotiated_price_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '议价记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for serve_quoted_price
-- ----------------------------
DROP TABLE IF EXISTS `serve_quoted_price`;
CREATE TABLE `serve_quoted_price`  (
  `serve_quoted_price_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '服务订单报价ID',
  `serve_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅认证ID',
  `worker_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '工人(师傅)用户ID',
  `quoted_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '报价金额',
  `quoted_message` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '报价留言',
  `assign_status` tinyint NULL DEFAULT 0 COMMENT '指派状态（0：待指派 1：已指派）',
  `negotiated_status` tinyint NULL DEFAULT -1 COMMENT '议价状态（-1：未议价 0：议价中 1：同意议价 2：拒绝议价）',
  `negotiated_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '议价金额',
  `negotiated_time` datetime NULL DEFAULT NULL COMMENT '议价时间',
  `negotiated_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '议价理由',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  `new_quoted_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '报价金额不被议价金额覆盖的',
  PRIMARY KEY (`serve_quoted_price_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '服务订单报价' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for serve_type
-- ----------------------------
DROP TABLE IF EXISTS `serve_type`;
CREATE TABLE `serve_type`  (
  `serve_type_id` bigint NOT NULL AUTO_INCREMENT COMMENT '服务类型ID',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父级id',
  `type_level` tinyint NULL DEFAULT 1 COMMENT '分类等级(1：一级 2：二级 3：三级)',
  `type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '类型名称',
  `type_icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '类型图标',
  `sort_num` int NULL DEFAULT 0 COMMENT '排序',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态(0:不显示 1:显示)',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  `address_status` tinyint NULL DEFAULT 0 COMMENT '地址状态（0:无地址 1:一个地址 2:两个地址）',
  PRIMARY KEY (`serve_type_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 70 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '服务类型' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for service_order
-- ----------------------------
DROP TABLE IF EXISTS `service_order`;
CREATE TABLE `service_order`  (
  `service_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '服务订单ID',
  `order_sn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT 'order_sn',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `service_date` date NULL DEFAULT NULL COMMENT '服务日期',
  `subscribe_time_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '预约时间ID',
  `start_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '开始时间',
  `end_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '结束时间',
  `one_serve_type_id` bigint NULL DEFAULT NULL COMMENT '一级服务ID',
  `two_serve_type_id` bigint NULL DEFAULT NULL COMMENT '二级服务ID',
  `three_serve_type_id` bigint NULL DEFAULT NULL COMMENT '三级服务ID',
  `one_serve_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '一级服务名称',
  `two_serve_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '二级服务名称',
  `three_serve_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '三级服务名称',
  `address_status` tinyint NULL DEFAULT 0 COMMENT '地址状态（0=无地址,1=一个地址,2=两个地址）',
  `quotation_mode` tinyint NULL DEFAULT 0 COMMENT '报价方式(1=固定价格,2=对方报价,3=自己报价)',
  `service_explain` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '服务说明',
  `explain_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '说明图片',
  `explain_voice` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '说明语音',
  `service_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '服务价格',
  `order_status` tinyint NULL DEFAULT 0 COMMENT '订单状态(1=待支付,2=待报价,3=待接单,4=待工作,5=工作中,6=待验收,7=待评价,8=已完成,9=已取消,10=已关闭,11=退款售后)',
  `work_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅用户ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '师傅认证ID',
  `service_pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '服务应付金额',
  `service_pay_status` tinyint NULL DEFAULT 0 COMMENT '服务金额支付状态（ 0：未支付,1：已支付）',
  `service_pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务金额支付方式（JSAPI=微信小程序支付,platform=后台支付,free=免费支付,APP=微信支付,alipay_app=支付宝支付）',
  `service_pay_time` datetime NULL DEFAULT NULL COMMENT '服务金额支付时间',
  `service_trade_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务金额支付流水号',
  `subjoin_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '附加金额',
  `subjoin_pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '附加应付金额',
  `subjoin_pay_status` tinyint NULL DEFAULT 0 COMMENT '附加金额支付状态（ 0：未支付,1：已支付）',
  `subjoin_pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '附加金额支付方式（JSAPI=微信小程序支付,platform=后台支付,free=免费支付,APP=微信支付,alipay_app=支付宝支付）',
  `subjoin_pay_time` datetime NULL DEFAULT NULL COMMENT '附加金额支付时间',
  `subjoin_trade_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '附加金额支付流水号',
  `finish_time` datetime NULL DEFAULT NULL COMMENT '订单完成时间',
  `close_time` datetime NULL DEFAULT NULL COMMENT '订单关闭时间',
  `cancel_time` datetime NULL DEFAULT NULL COMMENT '订单取消时间',
  `cancel_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '订单取消原因',
  `cancel_reason_details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '取消原因详情',
  `cancel_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '取消原因图片',
  `refund_status` tinyint NULL DEFAULT 0 COMMENT '退款状态（-1=未申请,0=申请中,1=已同意,2=已拒绝）',
  `refund_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '订单退款原因',
  `refund_reason_details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '退款原因详情',
  `refund_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '退款原因图片',
  `refund_time` datetime NULL DEFAULT NULL COMMENT '退款时间',
  `quoted_status` tinyint NULL DEFAULT 0 COMMENT '报价状态(0=无人报价,1=有人报价)',
  `before_order_status` tinyint NULL DEFAULT 0 COMMENT '申请售后前订单状态',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `cover_picture` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '封面图',
  `service_project_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务项目',
  `subjoin_order_sn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT 'subjoin_order_sn',
  `completion_explain` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '完工说明',
  `completion_picture` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '完工图片',
  `finish_type` tinyint NULL DEFAULT 0 COMMENT '完成类型(1:客户完成 2:系统完成)',
  `worker_earn_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '师傅赚的金额',
  `platform_earn_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '平台赚的金额',
  `exception_status` tinyint NULL DEFAULT 0 COMMENT '异常状态(0=正常,1=异常)',
  `exception_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '异常原因',
  `receive_time` datetime NULL DEFAULT NULL COMMENT '接单时间',
  `work_time` datetime NULL DEFAULT NULL COMMENT '上门时间',
  `completion_time` datetime NULL DEFAULT NULL COMMENT '完工时间',
  `payable_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '应付金额',
  `token_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '通证金额',
  `actual_pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '实际支付金额(拉起支付付款的金额)',
  `token_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '通证钱包ID',
  `cash_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '现金钱包ID',
  `ai_sync_order_status` tinyint NULL DEFAULT NULL COMMENT 'ai服务订单状态(0否 1是)',
  `cash_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '使用现金钱包总金额',
  `predict_token_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '通证金额',
  `token_transaction_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '通证交易单号',
  `enterprise_cash_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '企业现金收益',
  `enterprise_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '企业通证收益',
  `user_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '用户通证收益',
  `middle_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '中台通证收益',
  `invitation_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '邀请人通证收益',
  `reflow_token_amount` decimal(10, 2) NULL DEFAULT NULL COMMENT '回流通证',
  `commission_status` tinyint(1) NULL DEFAULT 0 COMMENT '分佣状态（0未分佣 1已分佣 2已到账）',
  `mount_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '挂载商品用户id',
  `live_stream_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '直播ID',
  PRIMARY KEY (`service_order_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '服务订单' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for service_project
-- ----------------------------
DROP TABLE IF EXISTS `service_project`;
CREATE TABLE `service_project`  (
  `service_project_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '服务项目ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `one_serve_type_id` bigint NULL DEFAULT NULL COMMENT '一级服务ID',
  `two_serve_type_id` bigint NULL DEFAULT NULL COMMENT '二级服务ID',
  `three_serve_type_id` bigint NULL DEFAULT NULL COMMENT '三级服务ID',
  `one_serve_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '一级服务名称',
  `two_serve_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '二级服务名称',
  `three_serve_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '三级服务名称',
  `platform_guarantee` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '平台保证',
  `price_type` tinyint NULL DEFAULT 0 COMMENT '价格类型(1:议价,2:定价)',
  `unit_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '单价',
  `province_code` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '省编码(多选)',
  `province` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '省(多选)',
  `city_code` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '市编码(多选)',
  `city` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '市(多选)',
  `county_code` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '区县编码(多选)',
  `county` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '区县(多选)',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '服务描述',
  `description_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '描述图片',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态(0:不显示 1:显示)',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  `cover_picture` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '封面图',
  `main_picture` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '轮播图',
  `address_status` tinyint NULL DEFAULT 0 COMMENT '地址状态（0:无地址 1:一个地址 2:两个地址）',
  `sales_num` bigint NULL DEFAULT 0 COMMENT '销量',
  PRIMARY KEY (`service_project_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '服务项目' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for session_event
-- ----------------------------
DROP TABLE IF EXISTS `session_event`;
CREATE TABLE `session_event`  (
  `session_event_id` bigint NOT NULL AUTO_INCREMENT COMMENT '会话session映射表id',
  `conversation_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT 'AI会话ID',
  `session_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '回调会话ID',
  `create_by` bigint NULL DEFAULT NULL COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint NULL DEFAULT NULL COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`session_event_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 9 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '会话session映射表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for shopping_cart
-- ----------------------------
DROP TABLE IF EXISTS `shopping_cart`;
CREATE TABLE `shopping_cart`  (
  `shopping_cart_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '购物车ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `goods_num` int NULL DEFAULT NULL COMMENT '商品数量',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `shopping_cart_type` tinyint NULL DEFAULT 1 COMMENT '购物车类型（1钢材 2机电）',
  PRIMARY KEY (`shopping_cart_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '购物车表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for special_apply
-- ----------------------------
DROP TABLE IF EXISTS `special_apply`;
CREATE TABLE `special_apply`  (
  `special_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '特惠申请ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '结束时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `store_goods_id` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `special_type` tinyint NULL DEFAULT 1 COMMENT '特惠类型（1优惠特卖 2天天低价）',
  `goods_name` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  PRIMARY KEY (`special_apply_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '特惠申请表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for special_apply_detail
-- ----------------------------
DROP TABLE IF EXISTS `special_apply_detail`;
CREATE TABLE `special_apply_detail`  (
  `special_apply_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '特惠申请明细ID',
  `special_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特惠申请ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `goods_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `spec_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格名称',
  `thumb` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '缩略图',
  `market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品价格',
  `special_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '特惠价格',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存',
  `goods_num` int NULL DEFAULT 0 COMMENT '商品数量',
  `start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开始时间',
  `end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '结束时间',
  PRIMARY KEY (`special_apply_detail_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '特惠申请明细表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for stock
-- ----------------------------
DROP TABLE IF EXISTS `stock`;
CREATE TABLE `stock`  (
  `stock_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '库存ID',
  `specification_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格型号',
  `units` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `brand` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品名称',
  `classify` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产品类别',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '0:否 1:删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态 0：显示 1：隐藏',
  `sort_num` bigint NULL DEFAULT 1 COMMENT '排序，数字越小越靠前',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者id',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `no_tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税进价',
  `tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税销售价',
  `tax_unit_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '含税进价',
  `no_tax_sales_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '不含税销售价',
  `tax_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '税率（%）',
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商管理id',
  `supplier_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商名称',
  `purchase_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '采购编号',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存数量',
  `report_stock_num` int NULL DEFAULT 0 COMMENT '报备数量',
  `wait_stock_num` int NULL DEFAULT 0 COMMENT '等待出库数量',
  `safety_stock_num` int NULL DEFAULT 0 COMMENT '安全库存数量',
  `max_stock_num` int NULL DEFAULT 0 COMMENT '最高库存数量',
  PRIMARY KEY (`stock_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '库存表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store
-- ----------------------------
DROP TABLE IF EXISTS `store`;
CREATE TABLE `store`  (
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '店铺ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `short_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺简称',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '所在城市ID',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺地址',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址纬度',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺分类ID',
  `steel_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '钢材分类ID',
  `business_label` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经营标签',
  `steel_business_label` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '钢材经营标签',
  `electromechanical_business_label` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机电经营标签',
  `logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺logo',
  `business_license` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '营业执照',
  `id_card_front_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证正面照片',
  `id_card_back_photo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证背面照片',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0审核中 1已通过 2已拒绝）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `grade` decimal(10, 2) NULL DEFAULT 5.00 COMMENT '店铺评分',
  `store_type` tinyint NULL DEFAULT 1 COMMENT '店铺类型（1商家 2门店(附近店) 3厂家 4销售商 5自营店）',
  `brief_introduction` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '店铺简介',
  `photo_wall` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '照片墙',
  `store_photo` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '店铺环境照片',
  `pick_up_status` tinyint NULL DEFAULT 0 COMMENT '是否支持到店自提（0不支持 1支持）',
  `delivery_status` tinyint NULL DEFAULT 0 COMMENT '是否支持商家配送（0不支持 1支持）',
  `logistics_status` tinyint NULL DEFAULT 0 COMMENT '是否支持物流配送（0不支持 1支持）',
  `total_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '总收益',
  `remaining_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '余额',
  `withdrawal_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `frozen_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '冻结金额',
  `wait_entry_amount` decimal(12, 2) NULL DEFAULT 0.00 COMMENT '待入账金额',
  `default_status` tinyint NULL DEFAULT 0 COMMENT '默认状态（0否 1是）',
  `starting_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '起送价',
  `delivery_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '配送费',
  `full_reduce_delivery_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '满减配送费',
  `start_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '休息开始时间',
  `end_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '营业结束时间',
  `edit_audit_status` tinyint NULL DEFAULT -1 COMMENT '资料编辑审核状态（-1未提交 0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '资料编辑审核拒绝原因',
  `business_status` tinyint NULL DEFAULT 0 COMMENT '营业状态（0休息 1营业）',
  `sales` int NULL DEFAULT 0 COMMENT '销量',
  `month_sales` int NULL DEFAULT 0 COMMENT '月销量',
  `good_rate` decimal(10, 2) NULL DEFAULT 100.00 COMMENT '好评率',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  `remarks` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '备注',
  `join_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '加盟费',
  `join_price_refund_status` tinyint NULL DEFAULT 0 COMMENT '加盟费退款状态（0未退款 1已退款）',
  `collection_num` int NULL DEFAULT 0 COMMENT '收藏数量',
  `order_num` int NULL DEFAULT NULL COMMENT '店铺序号',
  `business_hours` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '营业时间',
  `top_status` tinyint NULL DEFAULT 0 COMMENT '置顶状态（0否 1是）',
  `top_time` datetime NULL DEFAULT NULL COMMENT '置顶时间',
  `opening_hours` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '营业时间',
  `guarantee_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '保障描述',
  `business_qualification` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '商家资质',
  `logoff_apply_status` tinyint NULL DEFAULT -1 COMMENT '注销申请状态（-1未申请 0审核中 1已通过 2已拒绝）',
  `logoff_refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '注销拒绝原因',
  `store_nature` tinyint NULL DEFAULT 1 COMMENT '店铺性质（1个人 2企业）',
  `disable_status` tinyint NULL DEFAULT 0 COMMENT '禁用状态（0正常 1禁用）',
  `disable_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '禁用原因',
  `enterprise_nature` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业性质',
  `unified_social_credit_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '统一社会信用代码',
  `bank_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行账户',
  `bank_card_number` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行卡号',
  `bank_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行名称',
  `email` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '邮箱',
  `legal_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人名称',
  `legal_identity_card` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人身份证号',
  `legal_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人电话',
  `store_channel` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺频道（1钢材 2机电）',
  `current_channel` tinyint NULL DEFAULT NULL COMMENT '当前频道（1钢材 2机电）',
  `other_qualification` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '其他资质',
  `contract_num` int NULL DEFAULT 0 COMMENT '合同数量',
  `corporate_seal` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业公章',
  `recommend_status` tinyint NULL DEFAULT 0 COMMENT '推荐状态（0否 1是）',
  `recommend_time` datetime NULL DEFAULT NULL COMMENT '推荐时间',
  `deposit_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '保证金',
  `deposit_price_refund_status` tinyint NULL DEFAULT 0 COMMENT '保证金退款状态（0未退款 1已退款）',
  `goods_type` tinyint NULL DEFAULT NULL COMMENT '可添加商品类型（1同城购商品 2全国购商品 3自营商品 4批发商品）',
  PRIMARY KEY (`store_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '店铺表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_activities
-- ----------------------------
DROP TABLE IF EXISTS `store_activities`;
CREATE TABLE `store_activities`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '活动ID',
  `activity_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '活动名称',
  `activity_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '活动描述',
  `activity_type` tinyint NOT NULL DEFAULT 1 COMMENT '活动类型(1:免邮活动 2:折扣活动 3:秒杀活动等)',
  `start_time` datetime NOT NULL COMMENT '活动开始时间',
  `goods_ids` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '关联商品ids',
  `end_time` datetime NOT NULL COMMENT '活动结束时间',
  `banner_image_url` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '活动横幅图片URL',
  `redirect_url` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '点击跳转链接',
  `status` tinyint NOT NULL DEFAULT 1 COMMENT '活动状态(0:下架 1:上线)',
  `priority` int NOT NULL DEFAULT 0 COMMENT '展示优先级(数值越大越靠前)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_status_time`(`status`, `start_time`, `end_time`) USING BTREE,
  INDEX `idx_priority`(`priority`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '店铺活动表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_apply
-- ----------------------------
DROP TABLE IF EXISTS `store_apply`;
CREATE TABLE `store_apply`  (
  `store_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '店铺申请ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `short_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺简称',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '所在城市ID',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺地址',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址纬度',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '店铺分类ID',
  `steel_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '钢材分类ID',
  `business_label` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经营标签',
  `logo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺logo',
  `business_license` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '营业执照',
  `id_card_front_photo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证正面照片',
  `id_card_back_photo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '身份证背面照片',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0审核中 1已通过 2已拒绝）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `store_type` tinyint NULL DEFAULT 1 COMMENT '店铺类型（1商家 2门店(附近店) 3厂家 4销售商）',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  `pay_status` tinyint NULL DEFAULT 0 COMMENT '支付状态（0未支付 1已支付）',
  `remarks` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '备注',
  `pick_up_status` tinyint NULL DEFAULT 0 COMMENT '是否支持到店自提（0不支持 1支持）',
  `delivery_status` tinyint NULL DEFAULT 0 COMMENT '是否支持商家配送（0不支持 1支持）',
  `logistics_status` tinyint NULL DEFAULT 0 COMMENT '是否支持物流配送（0不支持 1支持）',
  `delivery_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '配送费  ',
  `full_reduce_delivery_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '满减配送费 ',
  `photo_wall` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '照片墙',
  `store_photo` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺环境照片',
  `brief_introduction` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '店铺简介',
  `opening_hours` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '营业时间',
  `guarantee_description` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '保障描述',
  `business_qualification` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '商家资质',
  `store_nature` tinyint NULL DEFAULT 1 COMMENT '店铺性质（1个人 2企业）',
  `enterprise_nature` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业性质',
  `unified_social_credit_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '统一社会信用代码',
  `business_area_distance` decimal(10, 2) NULL DEFAULT NULL COMMENT '经营地域范围(km)',
  `store_channel` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺频道（1钢材 2机电）',
  `current_channel` tinyint NULL DEFAULT NULL COMMENT '当前频道（1钢材 2机电）',
  `bank_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行账户',
  `bank_card_number` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行卡号',
  `bank_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行名称',
  `other_qualification` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '其他资质',
  `email` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '邮箱',
  `legal_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人名称',
  `legal_identity_card` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人身份证号',
  `legal_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人电话',
  `jun_zi_qian_status` tinyint NULL DEFAULT -1 COMMENT '君子签审核状态（-1未申请 0正在申请 1通过 2驳回）',
  `jun_zi_qian_msg` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '君子签驳回原因',
  `corporate_seal` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业公章',
  `join_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '加盟费',
  `deposit_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '保证金',
  `order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单号',
  `pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '实付金额',
  `pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付方式（APP微信 alipay_app支付宝 platform平台支付 free免费支付）',
  `app_id` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'AppId',
  `trade_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付流水号',
  `pay_time` datetime NULL DEFAULT NULL COMMENT '支付时间',
  `commission_status` tinyint NULL DEFAULT 0 COMMENT '分佣状态（0未分佣 1已分佣）',
  `maker_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '创客收益',
  PRIMARY KEY (`store_apply_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '店铺申请表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_class
-- ----------------------------
DROP TABLE IF EXISTS `store_class`;
CREATE TABLE `store_class`  (
  `store_class_id` bigint NOT NULL AUTO_INCREMENT COMMENT '店铺分类ID',
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '分类名称',
  `icon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '分类图标',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父类ID',
  `sort_num` int NULL DEFAULT NULL COMMENT '顺序',
  `level` int NULL DEFAULT NULL COMMENT '级别',
  `show_status` tinyint NULL DEFAULT 0 COMMENT '显示状态（0隐藏 1显示）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `store_type` tinyint NULL DEFAULT 1 COMMENT '店铺类型',
  `store_channel` tinyint NULL DEFAULT NULL COMMENT '店铺频道',
  `min_commission_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '最低让利比例(%)',
  PRIMARY KEY (`store_class_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 49 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '店铺分类表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_edit_record
-- ----------------------------
DROP TABLE IF EXISTS `store_edit_record`;
CREATE TABLE `store_edit_record`  (
  `store_edit_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '店铺修改记录ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `logo` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺logo',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `short_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺简称',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺地址',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址纬度',
  `store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺分类ID',
  `steel_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '钢材分类ID',
  `business_label` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经营标签',
  `brief_introduction` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺简介',
  `photo_wall` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '照片墙',
  `store_photo` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺环境照片',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0待审核 1已通过 2已拒绝）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  `remarks` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '备注',
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `pick_up_status` tinyint NULL DEFAULT 0 COMMENT '是否支持到店自提（0不支持 1支持）',
  `delivery_status` tinyint NULL DEFAULT 0 COMMENT '是否支持商家配送（0不支持 1支持）',
  `logistics_status` tinyint NULL DEFAULT 0 COMMENT '是否支持物流配送（0不支持 1支持）',
  `delivery_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '配送费',
  `full_reduce_delivery_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '满减配送费',
  `business_license` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '营业执照',
  `hotel_class_id` bigint NULL DEFAULT NULL COMMENT '酒店类型ID',
  `hotel_class_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '酒店类型',
  `hotel_star` int NULL DEFAULT NULL COMMENT '酒店星级',
  `hotel_star_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '星级名称',
  `hotel_facilities_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '酒店设施ID',
  `hotel_facilities_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '酒店设施名称',
  `consume_range_id` bigint NULL DEFAULT NULL COMMENT '消费区间ID',
  `min_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '最小价格',
  `max_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '最大价格',
  `booking_tips` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '预订须知',
  `breakfast_status` tinyint NULL DEFAULT 0 COMMENT '是否包含早餐（0不包含 1包含）',
  `opening_hours` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '营业时间',
  `guarantee_description` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '保障描述',
  `business_qualification` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '商家资质',
  `enterprise_nature` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业性质',
  `unified_social_credit_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '统一社会信用代码',
  `business_area_distance` decimal(10, 2) NULL DEFAULT NULL COMMENT '经营地域范围(km)',
  `other_qualification` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '其他资质',
  `bank_account` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行账户',
  `bank_card_number` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行卡号',
  `bank_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行名称',
  `legal_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人名称',
  `legal_identity_card` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人身份证号',
  `legal_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '法人电话',
  `corporate_seal` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业公章',
  PRIMARY KEY (`store_edit_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '店铺资料修改记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_goods
-- ----------------------------
DROP TABLE IF EXISTS `store_goods`;
CREATE TABLE `store_goods`  (
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '城市ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `goods_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `thumb` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '缩略图',
  `pictures` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品图片',
  `detail_pictures` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品详情图片',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '商品描述',
  `sale_status` tinyint NULL DEFAULT 0 COMMENT '出售状态（0下架 1上架）',
  `store_goods_class_id` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品分类ID',
  `store_spec_type_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `guarantee_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '商品保障ID',
  `goods_guarantee` json NULL COMMENT '商品保障内容',
  `audit_status` tinyint NULL DEFAULT -1 COMMENT '审核状态（-1未提交 0审核中 1已通过 2已拒绝）',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝原因',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `buy_store_status` tinyint NULL DEFAULT 0 COMMENT '购买商城状态（0下架 1上架）',
  `self_store_status` tinyint NULL DEFAULT 0 COMMENT '自营商城状态（0下架 1上架）',
  `integral_store_status` tinyint NULL DEFAULT 0 COMMENT '消费金商城状态（0下架 1上架）',
  `seckill_store_status` tinyint NULL DEFAULT 0 COMMENT '秒杀商城状态（0下架 1上架）',
  `special_store_status` tinyint NULL DEFAULT 0 COMMENT '特惠商城状态（0下架 1上架）',
  `wholesale_store_status` tinyint NULL DEFAULT 0 COMMENT '批发商城状态（0下架 1上架）',
  `sort_num` int NULL DEFAULT 0 COMMENT '顺序',
  `one_store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台一级分类ID',
  `two_store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台二级分类ID',
  `three_store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台三级分类ID',
  `four_store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台四级分类ID',
  `store_spec_status` tinyint NULL DEFAULT 0 COMMENT '规格类型（0无规格 1单规格 2多规格）',
  `cashback_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '返现比例',
  `back_integral_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '返积分比例',
  `keyword` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '搜索关键字',
  `service_provider_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '服务商分佣比例',
  `one_commission_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '一级分销比例',
  `two_commission_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '二级分销比例',
  `freight_status` tinyint NULL DEFAULT 1 COMMENT '快递运费计算方式（1统一运费 2运费模板）',
  `freight_money` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '统一运费',
  `freight_template_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运费模板ID',
  `video` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品视频',
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `original_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '原价',
  `market_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '现价',
  `factory_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '出厂价',
  `wholesale_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '批发价',
  `min_wholesale_num` int NULL DEFAULT 0 COMMENT '起批数量',
  `integral` int NULL DEFAULT 0 COMMENT '消费金',
  `integral_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '消费金组合价格',
  `seckill_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '秒杀价',
  `sales` int NULL DEFAULT 0 COMMENT '销量',
  `month_sales` int NULL DEFAULT 0 COMMENT '月销量',
  `virtual_sales` int NULL DEFAULT 0 COMMENT '虚拟销量',
  `special_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '特价价格',
  `goods_parameter` json NULL COMMENT '商品参数',
  `top_status` tinyint NULL DEFAULT 0 COMMENT '置顶状态（0不置顶 1置顶）',
  `recommend_status` tinyint NULL DEFAULT 0 COMMENT '推荐状态（0下架 1上架）',
  `store_type` tinyint NULL DEFAULT 1 COMMENT '店铺类型（1商家 2门店(附近店) 3厂家 4销售商 5自营店）',
  `weight` decimal(10, 4) NULL DEFAULT 1.0000 COMMENT '商品重量(吨)',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存数量',
  `integral_deduct_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '积分抵扣比例(%)',
  `special_start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特惠开始时间',
  `special_end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特惠结束时间',
  `grade` decimal(10, 2) NULL DEFAULT 5.00 COMMENT '商品评分',
  `good_rate` decimal(10, 2) NULL DEFAULT 100.00 COMMENT '好评率',
  `min_purchase_num` int NULL DEFAULT 0 COMMENT '起购数量',
  `limit_purchase_num` int NULL DEFAULT 0 COMMENT '限购数量',
  `pick_up_type` tinyint NULL DEFAULT 1 COMMENT '提货类型（1现货 2开机提货）',
  `pick_up_start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提货开始时间',
  `pick_up_end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提货结束时间',
  `base_different_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '基差价格',
  `base_different_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '基差编码',
  `spec_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '规格名称',
  `brand_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '品牌ID',
  `store_class_id` bigint NULL DEFAULT NULL COMMENT '店铺分类ID',
  `store_house_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '仓库ID',
  `house_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '仓库名称',
  `location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '所在地区(包含省市区街道)',
  `detail_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  `unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `product_quality` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品品质',
  `store_channel` tinyint NULL DEFAULT NULL COMMENT '店铺频道（1钢材 2机电）',
  `goods_type` tinyint NULL DEFAULT NULL COMMENT '商品类型（1同城购商品 2全国购商品 3自营商品 4批发商品）',
  `delivery_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '运费',
  `material_quality` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '材质',
  `goods_origin` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '产地',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `delivery_place` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '存货地',
  `apply_time` datetime NULL DEFAULT NULL COMMENT '申请时间',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `inventory_warning_limit` int NULL DEFAULT 0 COMMENT '库存预警值',
  `commission_rate` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '代销佣金比例(%)',
  `ranking_desc` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '排名描述',
  `seckill_status` tinyint NULL DEFAULT 0 COMMENT '秒杀状态（0否 1是）',
  `special_status` tinyint NULL DEFAULT 0 COMMENT '特惠状态（0否 1是）',
  `one_store_class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台一级分类名称',
  `two_store_class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台二级分类名称',
  `three_store_class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台三级分类名称',
  `four_store_class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台四级分类名称',
  `warehouse_status` tinyint(1) NULL DEFAULT 0 COMMENT '商品库状态（0否 1是）',
  `consignment_sales_status` tinyint(1) NULL DEFAULT 0 COMMENT '是否是代销商品（0否 1是）',
  `drop_ship_status` tinyint(1) NULL DEFAULT 0 COMMENT '一键代发状态（0否 1是）',
  `goods_source` tinyint(1) NULL DEFAULT 1 COMMENT '商品来源（1自己添加 2商品库）',
  `original_store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商家ID',
  `original_store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商家名称',
  `global_store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '全局商品ID',
  `original_store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商品ID',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '原项目ID',
  `original_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原项目名称',
  `one_standard_class_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '标准一级分类ID',
  `two_standard_class_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '标准二级分类ID',
  `three_standard_class_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '标准三级分类ID',
  `one_standard_class_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '标准一级分类名称',
  `two_standard_class_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '标准二级分类名称',
  `three_standard_class_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '标准三级分类名称',
  `consignment_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '代销价',
  `supply_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '供货价',
  `suggest_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '建议零售价',
  `source_type` tinyint(1) NULL DEFAULT 1 COMMENT '来源类型（1供应商 2企业）',
  `promoter_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '推广员价',
  `employee_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '员工价',
  `agent_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '区域代理商价',
  `audience_type` tinyint(1) NULL DEFAULT 2 COMMENT '受众群体(0:全员,1:企业，2:用户)',
  `group_buying_status` tinyint NULL DEFAULT 0 COMMENT '拼团状态（0否 1是）',
  `group_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '拼团价格',
  `group_member_num` int NULL DEFAULT NULL COMMENT '拼团人数',
  `group_type` int NULL DEFAULT NULL COMMENT '拼团类型(1人数 2数量)',
  `group_good_num` int NULL DEFAULT NULL COMMENT '拼团限制数量',
  `seckill_group_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '秒杀拼团价格',
  PRIMARY KEY (`store_goods_id`) USING BTREE,
  INDEX `idx_store_id`(`store_id`) USING BTREE COMMENT '店铺ID索引',
  INDEX `idx_goods_name`(`goods_name`(20)) USING BTREE COMMENT '商品名称索引',
  FULLTEXT INDEX `goods_name`(`goods_name`) WITH PARSER `ngram`
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商品表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_goods_browse_record
-- ----------------------------
DROP TABLE IF EXISTS `store_goods_browse_record`;
CREATE TABLE `store_goods_browse_record`  (
  `store_goods_browse_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品浏览记录ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`store_goods_browse_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商品浏览记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_goods_class
-- ----------------------------
DROP TABLE IF EXISTS `store_goods_class`;
CREATE TABLE `store_goods_class`  (
  `store_goods_class_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品分类ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `class_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '分类名称',
  `order_num` int NULL DEFAULT 0 COMMENT '顺序',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `house_class_id` bigint NULL DEFAULT NULL COMMENT '房型分类ID(酒店)',
  PRIMARY KEY (`store_goods_class_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商家商品分类表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_goods_spec
-- ----------------------------
DROP TABLE IF EXISTS `store_goods_spec`;
CREATE TABLE `store_goods_spec`  (
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品规格ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '城市ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `store_spec_type_id` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '商品规格类型ID',
  `store_spec_item_id` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '商品规格名称ID',
  `store_spec_type_index` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格类型序号',
  `store_spec_item_index` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格名称序号',
  `store_spec_type` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格类型',
  `store_spec_name` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格名称',
  `thumb` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '缩略图',
  `original_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '原价',
  `market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '现价',
  `sale_status` tinyint NULL DEFAULT 0 COMMENT '出售状态（0下架 1上架）',
  `stock_num` int NULL DEFAULT 0 COMMENT '库存数量',
  `sales` int NULL DEFAULT 0 COMMENT '销量',
  `month_sales` int NULL DEFAULT 0 COMMENT '月销量',
  `virtual_sales` int NULL DEFAULT 0 COMMENT '虚拟销量',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `special_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '特价价格',
  `special_status` tinyint NULL DEFAULT 0 COMMENT '特价状态（0否 1是）',
  `good_rate` decimal(10, 2) NULL DEFAULT 100.00 COMMENT '好评率',
  `special_audit_status` tinyint NULL DEFAULT -1 COMMENT '特价审核状态（-1未申请 0审核中 1已通过 2已拒绝）',
  `special_start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特价开始时间',
  `special_end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特价结束时间',
  `factory_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '出厂价',
  `wholesale_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '批发价',
  `min_wholesale_num` int NULL DEFAULT 0 COMMENT '起批数量',
  `integral` int NULL DEFAULT 0 COMMENT '消费金',
  `integral_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '消费金组合价格',
  `seckill_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '秒杀价',
  `weight` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品重量(kg)',
  `temporary_storage_status` tinyint NULL DEFAULT 0 COMMENT '暂存状态（0否 1是）',
  `tag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '每次更新的标识',
  `store_type` tinyint NULL DEFAULT 1 COMMENT '店铺类型（店铺类型（1采购商 2经销商 3厂家 4生产加工）',
  `unit` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位',
  `seckill_status` tinyint NULL DEFAULT 0 COMMENT '秒杀状态（0否 1是）',
  `seckill_audit_status` tinyint NULL DEFAULT -1 COMMENT '秒杀审核状态（-1未申请 0审核中 1已通过 2已拒绝）',
  `seckill_start_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀开始时间',
  `seckill_end_time` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀结束时间',
  `seckill_stock_num` int NULL DEFAULT 0 COMMENT '秒杀库存',
  `special_stock_num` int NULL DEFAULT 0 COMMENT '特惠库存',
  `seckill_apply_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀申请明细ID',
  `special_apply_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特惠申请明细ID',
  `suggest_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '建议零售价',
  `consignment_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '用户代销价',
  `promoter_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '推广员价',
  `employee_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '员工价',
  `agent_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '区域代理商价',
  `original_store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '原商品规格ID',
  `supply_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '供货价',
  `group_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '拼团价格',
  `seckill_group_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '秒杀拼团价格',
  PRIMARY KEY (`store_goods_spec_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商品规格表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_hot_search_stats
-- ----------------------------
DROP TABLE IF EXISTS `store_hot_search_stats`;
CREATE TABLE `store_hot_search_stats`  (
  `keyword` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `count` bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (`keyword`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '店铺热搜统计表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_order
-- ----------------------------
DROP TABLE IF EXISTS `store_order`;
CREATE TABLE `store_order`  (
  `store_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商城订单ID',
  `user_id` bigint NULL DEFAULT NULL COMMENT '后台用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '城市ID',
  `order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单号',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `address_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户地址ID',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '所在地区(包含省市区街道)',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `order_status` tinyint NULL DEFAULT 1 COMMENT '订单状态（1待付款 2待自提 3待配送 4待发货 5待收货 6已完成 7退款售后 8已取消 9已关闭）',
  `evaluate_status` tinyint NULL DEFAULT 0 COMMENT '评价状态（0未评价 1已评价）',
  `pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付方式（APP微信 alipay_app支付宝 platform后台支付 free免费支付）',
  `pay_time` datetime NULL DEFAULT NULL COMMENT '支付时间',
  `trade_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付流水号',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单备注信息',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `delivery_time` datetime NULL DEFAULT NULL COMMENT '发货时间',
  `complete_time` datetime NULL DEFAULT NULL COMMENT '完成时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `refund_time` datetime NULL DEFAULT NULL COMMENT '退款申请时间',
  `refund_success_time` datetime NULL DEFAULT NULL COMMENT '退款成功时间',
  `refund_cause` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款原因',
  `refund_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '退款金额',
  `refund_explain` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款说明',
  `refund_url` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款照片',
  `refund_status` tinyint NULL DEFAULT -1 COMMENT '退款状态（-1未申请 0申请中 1已同意 2已拒绝）',
  `refuse_reason` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝退款原因',
  `total_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品总价',
  `delivery_price` decimal(10, 2) UNSIGNED NULL DEFAULT NULL COMMENT '配送费',
  `platform_account_coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台用户优惠券ID',
  `platform_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台优惠金额',
  `store_account_coupon_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺用户优惠券ID',
  `store_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '店铺优惠金额',
  `picking_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '取货码',
  `delivery_type` tinyint NULL DEFAULT NULL COMMENT '配送方式（1自提 2配送）',
  `pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '实付金额(除过优惠需要支付的金额)',
  `appointment_pick_up_start_time` datetime NULL DEFAULT NULL COMMENT '预计取货开始时间',
  `appointment_pick_up_end_time` datetime NULL DEFAULT NULL COMMENT '预计取货结束时间',
  `pick_up_time` datetime NULL DEFAULT NULL COMMENT '取货时间',
  `goods_num` int NULL DEFAULT NULL COMMENT '商品总数',
  `appointment_delivery_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '预计送达时间',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `appointment_pick_up_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '预计自提时间',
  `cancel_time` datetime NULL DEFAULT NULL COMMENT '取消时间',
  `cancel_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '取消原因',
  `cancel_explain` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '取消说明',
  `cancel_pictures` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '取消图片',
  `cancel_type` tinyint NULL DEFAULT NULL COMMENT '取消类型（1用户 2店铺）',
  `receive_time` datetime NULL DEFAULT NULL COMMENT '接单时间',
  `store_del_status` tinyint NULL DEFAULT 0 COMMENT '商家删除状态（0未删除 1已删除）',
  `preparation_time` datetime NULL DEFAULT NULL COMMENT '备货时间',
  `app_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'AppId',
  `store_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '商家收益',
  `real_store_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '真实商家收益',
  `cashback` decimal(10, 2) NULL DEFAULT NULL COMMENT '用户返现',
  `back_integral` int NULL DEFAULT 0 COMMENT '用户返积分',
  `service_provider_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '服务商收益',
  `one_commission_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '一级分销收益',
  `two_commission_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '二级分销收益',
  `platform_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台收益',
  `before_refund_status` tinyint NULL DEFAULT 0 COMMENT '申请退款前的订单状态',
  `order_type` tinyint NULL DEFAULT 1 COMMENT '订单类型（1普通订单 2批发订单 3消费金订单）',
  `store_type` tinyint NULL DEFAULT NULL COMMENT '店铺类型（1商家 2门店(附近店) 3厂家 4销售商 5自营店）',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `town_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇编码',
  `town` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '街道/乡镇',
  `total_integral` int NULL DEFAULT 0 COMMENT '订单总积分',
  `receive_status` tinyint NULL DEFAULT 0 COMMENT '收货状态（0未收到货 1已收到货）',
  `logistics_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流公司名称',
  `logistics_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流公司编码',
  `logistics_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流单号',
  `order_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '订单利润',
  `remaining_pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '余额支付金额',
  `new_account_status` tinyint NULL DEFAULT 0 COMMENT '新用户状态（0否 1是）',
  `service_provider_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务商ID',
  `one_store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '一级体验店ID',
  `two_store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '二级体验店ID',
  `commission_status` tinyint NULL DEFAULT 0 COMMENT '分佣状态（0未分佣 1已分佣 2已到账）',
  `refund_end_time` datetime NULL DEFAULT NULL COMMENT '退款截止时间（确认收货N天后，天数后台配置）',
  `cashback_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户返现记录ID（account_earnings_detail表）',
  `back_integral_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户返积分记录ID（integral_record表）',
  `store_profit_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商家收益记录ID（account_earnings_detail表）',
  `service_provider_profit_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务商收益记录ID（account_earnings_detail表）',
  `one_commission_profit_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '一级分销收益记录ID（account_earnings_detail表）',
  `two_commission_profit_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '二级分销收益记录ID（account_earnings_detail表）',
  `platform_profit_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台收益记录ID（commission_record表）',
  `member_store_level_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '会员注册商城价格档位ID',
  `logistics_error_status` tinyint NULL DEFAULT 0 COMMENT '物流信息查询错误状态（0正常 1错误）',
  `logistics_error_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流信息查询错误原因',
  `pull_pay_time` datetime NULL DEFAULT NULL COMMENT '拉起支付的时间',
  `read_status` tinyint NULL DEFAULT 0 COMMENT '已读状态（0未读 1已读）',
  `operator_order_status` tinyint NULL DEFAULT NULL COMMENT '运营商订单状态（1待发货 2待收货 3已收货）',
  `contract_apply_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '君子签电子合同编号',
  `sign_contract_status` tinyint NULL DEFAULT -1 COMMENT '签约合同状态（-1未发起 0未签 1已签 2拒签 3已保全）',
  `evaluate_time` datetime NULL DEFAULT NULL COMMENT '评价时间',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `store_logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺logo',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `store_contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺联系电话',
  `goods_name` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `sign_time` datetime NULL DEFAULT NULL COMMENT '签约时间',
  `account_del_status` tinyint NULL DEFAULT 0 COMMENT '用户删除状态（0未删除 1已删除）',
  `operator_del_status` tinyint NULL DEFAULT 0 COMMENT '运营中心删除状态（0未删除 1已删除）',
  `operator_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心用户ID',
  `partner_apply_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心ID',
  `operator_partner_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心名称',
  `operator_contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心联系人',
  `operator_contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心联系电话',
  `operator_location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心所在地区(包含省市区街道)',
  `operator_detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心详细地址',
  `operator_longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心经度',
  `operator_latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心纬度',
  `pay_order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付订单号',
  `delivery_pictures` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发货照片',
  `operator_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心订单ID',
  `confirm_status` tinyint NULL DEFAULT 0 COMMENT '商家确认收货状态（0未确认 1已确认）',
  `confirm_time` datetime NULL DEFAULT NULL COMMENT '商家确认收货时间',
  `operator_logistics_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心物流公司名称',
  `operator_logistics_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心物流公司编码',
  `operator_logistics_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '运营中心物流单号',
  `total_market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品出售总价',
  `one_maker_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '上级创客合伙人收益',
  `one_maker_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '上级创客合伙人ID',
  `one_operator_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '上级运营合伙人收益',
  `one_operator_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '上级运营合伙人ID',
  `province_operator_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '省级运营合伙人收益',
  `province_operator_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省级运营合伙人ID',
  `city_operator_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '市级运营合伙人收益',
  `city_operator_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市级运营合伙人ID',
  `county_operator_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '区县级运营合伙人收益',
  `county_operator_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县级运营合伙人ID',
  `town_operator_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '乡镇/街道级运营合伙人收益',
  `town_operator_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '乡镇/街道级运营合伙人ID',
  `project_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '项目合伙人收益',
  `project_partner_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目合伙人ID',
  `invoice_status` tinyint NULL DEFAULT 0 COMMENT '开票状态（0否 1是）',
  `invoice_time` datetime NULL DEFAULT NULL COMMENT '开票时间',
  `write_off_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '核销码',
  `write_off_time` datetime NULL DEFAULT NULL COMMENT '核销时间',
  `complaint_status` tinyint NULL DEFAULT 0 COMMENT '投诉状态（0否 1是）',
  `complaint_time` datetime NULL DEFAULT NULL COMMENT '投诉时间',
  `refundable_status` tinyint NULL DEFAULT 1 COMMENT '可退款状态（0否 1是）',
  `refund_apply_time` datetime NULL DEFAULT NULL COMMENT '退款申请时间',
  `refund_audit_time` datetime NULL DEFAULT NULL COMMENT '退款审核时间',
  `store_refund_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款订单ID',
  `auto_complete_time` datetime NULL DEFAULT NULL COMMENT '自动完成时间',
  `refund_type` tinyint NULL DEFAULT 1 COMMENT '退款类型（1仅退款 2退货退款）',
  `return_status` tinyint NULL DEFAULT -1 COMMENT '回寄状态（-1不需要回寄 0待寄出 1已寄出 2已收到）',
  `delivery_status` tinyint NULL DEFAULT 0 COMMENT '是否要配送（0否 1是）',
  `delivery_order_status` tinyint NULL DEFAULT NULL COMMENT '配送订单状态（1待接单 2待配送 3配送中 4已完成 5已取消）',
  `deliveryman_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送员ID',
  `deliveryman_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送员用户ID',
  `deliveryman_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送员名字',
  `deliveryman_contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送员联系电话',
  `deliveryman_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '配送员收益',
  `install_status` tinyint NULL DEFAULT 0 COMMENT '是否要安装（0否 1是）',
  `install_order_status` tinyint NULL DEFAULT NULL COMMENT '安装订单状态（1待接单 2待安装 3安装中 4已完成 5已取消）',
  `installman_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '安装员ID',
  `installman_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '安装员用户ID',
  `installman_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '安装员名字',
  `installman_contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '安装员联系电话',
  `installman_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '安装员收益',
  `install_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '安装费',
  `delivery_order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送安装订单号',
  `delivery_pay_status` tinyint NULL DEFAULT 0 COMMENT '配送安装支付状态（0未支付 1已支付）',
  `delivery_pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送安装支付方式（APP微信 alipay_app支付宝 platform后台支付 free免费支付）',
  `delivery_pay_time` datetime NULL DEFAULT NULL COMMENT '配送安装支付时间',
  `delivery_trade_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送安装支付流水号',
  `store_location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺所在地区(包含省市区街道)',
  `store_detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺详细地址',
  `store_longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺经度',
  `store_latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺纬度',
  `delivery_app_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '配送安装AppId',
  `delivery_receive_time` datetime NULL DEFAULT NULL COMMENT '配送接单时间',
  `arrival_time` datetime NULL DEFAULT NULL COMMENT '送达时间',
  `arrival_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '送达备注',
  `arrival_pictures` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '送达图片',
  `install_receive_time` datetime NULL DEFAULT NULL COMMENT '安装接单时间',
  `start_install_time` datetime NULL DEFAULT NULL COMMENT '开始安装时间',
  `install_complete_time` datetime NULL DEFAULT NULL COMMENT '安装完成时间',
  `install_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '安装备注',
  `install_pictures` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '安装图片',
  `maker_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '创客收益',
  `partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '合伙人收益',
  `industry_partner_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '行业合伙人收益',
  `delivery_commission_status` tinyint NULL DEFAULT 0 COMMENT '配送单分佣状态（0未分佣 1已分佣）',
  `goods_type` tinyint NULL DEFAULT NULL COMMENT '商品类型（1同城购商品 2全国购商品 3自营商品 4批发商品）',
  `wx_applet_openid` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信小程序openid',
  `consignment_sales_status` tinyint NULL DEFAULT 0 COMMENT '代销状态（0否 1是）',
  `consignment_sales_store_status` tinyint NULL DEFAULT 0 COMMENT '代销商家状态（0否 1是）',
  `project_id` bigint NULL DEFAULT NULL COMMENT '项目ID',
  `project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `original_store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商家ID',
  `original_store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商家名称',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '原项目ID',
  `original_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原项目名称',
  `cross_platform_status` tinyint NULL DEFAULT 0 COMMENT '跨平台订单状态（0否 1是）',
  `outsourcing_account_type` tinyint NULL DEFAULT 0 COMMENT '一键代发用户类型（0用户 1员工）',
  `outsourcing_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '一键代发用户id',
  `drop_ship_status` tinyint(1) NULL DEFAULT 0 COMMENT '一键代发状态（0否 1是）',
  `payable_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '应付金额(pay_price减通证金额)',
  `token_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '通证金额',
  `token_transaction_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '通证交易单号',
  `cash_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '现金金额',
  `actual_pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '实际支付金额(拉起支付付款的金额)',
  `token_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '通证钱包ID',
  `cash_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '现金钱包ID',
  `enterprise_cash_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '企业现金收益',
  `enterprise_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '企业通证收益',
  `user_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '用户通证收益',
  `middle_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '中台通证收益',
  `invitation_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '邀请人通证收益',
  `reflow_token_amount` decimal(10, 2) NULL DEFAULT NULL COMMENT '回流通证',
  `ai_sync_order_status` tinyint NULL DEFAULT NULL COMMENT 'ai商城订单状态(0否 1是)',
  `traffic_acquisition_plan_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '流量互导计划id',
  `original_customer_id` bigint NULL DEFAULT NULL COMMENT '原客户ID(店铺属于的客户)',
  `original_customer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原客户名称(店铺属于的客户)',
  PRIMARY KEY (`store_order_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商城订单表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_order_evaluate
-- ----------------------------
DROP TABLE IF EXISTS `store_order_evaluate`;
CREATE TABLE `store_order_evaluate`  (
  `store_order_evaluate_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商城订单评价ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城订单ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `store_goods_id` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `store_goods_spec_id` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `star` tinyint NULL DEFAULT NULL COMMENT '评价星级',
  `level` tinyint NULL DEFAULT NULL COMMENT '评价等级（1好评(5星) 2中评(3/4星) 3差评(1/2星)）',
  `content` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '评价内容',
  `pic` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '评价图片',
  `anonymous_status` tinyint NULL DEFAULT 0 COMMENT '匿名状态（0否 1是）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `store_order_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城订单商品ID',
  `evaluate_label` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '评价标签',
  `reply` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '评价回复',
  `hotel_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '酒店订单ID',
  `house_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '房间ID',
  `takeout_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '外卖订单ID',
  `takeout_order_goods_id` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '外卖订单商品ID',
  `serve_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务订单ID',
  `serve_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务ID',
  `serve_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '服务规格ID',
  `group_buy_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '团购订单ID',
  `store_goods_group_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品团购ID',
  `car_order_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '车辆订单ID',
  `travel_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '旅游订单ID',
  `travel_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '旅游ID',
  PRIMARY KEY (`store_order_evaluate_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商城订单评价表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_order_goods
-- ----------------------------
DROP TABLE IF EXISTS `store_order_goods`;
CREATE TABLE `store_order_goods`  (
  `store_order_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商城订单商品ID',
  `store_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城订单ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `thumb` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '缩略图',
  `goods_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `goods_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品单价',
  `goods_num` int NULL DEFAULT 0 COMMENT '商品数量',
  `goods_total_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品总价',
  `order_status` tinyint NULL DEFAULT 1 COMMENT '订单状态（1待付款 2待自提 3待配送 4待发货 5待收货 6已完成 7退款售后 8已取消 9已关闭）\'',
  `evaluate_status` tinyint NULL DEFAULT 0 COMMENT '评价状态（0未评价 1已评价）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `refund_apply_time` datetime NULL DEFAULT NULL COMMENT '退款申请时间',
  `refund_audit_time` datetime NULL DEFAULT NULL COMMENT '退款审核时间',
  `refund_success_time` datetime NULL DEFAULT NULL COMMENT '退款成功时间',
  `refund_cause` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款原因',
  `refund_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '退款金额',
  `refund_explain` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款说明',
  `refund_url` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款照片',
  `refund_status` tinyint NULL DEFAULT -1 COMMENT '退款状态（-1未申请 0申请中 1已同意 2已拒绝）',
  `refuse_reason` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝退款原因',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `platform_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台优惠金额',
  `store_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '店铺优惠金额',
  `pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '实付金额(除过优惠需要支付的金额)',
  `store_spec_name` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格名称',
  `before_refund_status` tinyint NULL DEFAULT 0 COMMENT '申请退款前的订单状态',
  `goods_integral` int NULL DEFAULT 0 COMMENT '商品积分',
  `goods_total_integral` int NULL DEFAULT 0 COMMENT '商品总积分',
  `remaining_pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '余额支付金额',
  `delivery_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '配送费',
  `goods_source` tinyint NULL DEFAULT 1 COMMENT '商品来源（1：普通 2：店庆 3：团购）',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '来源id(店庆商品规格ID 团购规格ID)',
  `market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品出售单价',
  `total_market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品出售总价',
  `goods_type` tinyint NULL DEFAULT NULL COMMENT '商品类型（1现货 2期货）',
  `seckill_status` tinyint NULL DEFAULT 0 COMMENT '秒杀状态（0否 1是）',
  `special_status` tinyint NULL DEFAULT 0 COMMENT '特惠状态（0否 1是）',
  `seckill_apply_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '秒杀申请明细ID',
  `special_apply_detail_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '特惠申请明细ID',
  `global_store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '全局商品ID',
  `original_store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商品ID',
  `project_id` bigint NULL DEFAULT NULL COMMENT '项目ID',
  `project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '项目名称',
  `original_store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商家ID',
  `original_store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原商家名称',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '原项目ID',
  `original_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '原项目名称',
  `platform_cross_platform_status` tinyint(1) NULL DEFAULT 0 COMMENT '平台优惠券是否跨平台（0否 1是）',
  `platform_commission_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台优惠券渠道佣金比例(%)',
  `platform_target_project_id` bigint NULL DEFAULT NULL COMMENT '平台优惠券渠道项目ID',
  `platform_target_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台优惠券渠道项目名称',
  `platform_target_commission` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台优惠券渠道项目佣金',
  `store_cross_platform_status` tinyint(1) NULL DEFAULT 0 COMMENT '店铺优惠券是否跨平台（0否 1是）',
  `store_commission_rate` decimal(10, 2) NULL DEFAULT NULL COMMENT '店铺优惠券渠道佣金比例(%)',
  `store_target_project_id` bigint NULL DEFAULT NULL COMMENT '店铺优惠券渠道项目ID',
  `store_target_project_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺优惠券渠道项目名称',
  `store_target_commission` decimal(10, 2) NULL DEFAULT NULL COMMENT '店铺优惠券渠道项目佣金',
  `payable_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '应付金额(pay_price减通证金额)',
  `token_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '通证金额',
  `cash_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '现金金额',
  `actual_pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '实际支付金额(拉起支付付款的金额)',
  PRIMARY KEY (`store_order_goods_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商城订单商品表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_purchase_record
-- ----------------------------
DROP TABLE IF EXISTS `store_purchase_record`;
CREATE TABLE `store_purchase_record`  (
  `store_purchase_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '店铺购买记录ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`store_purchase_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '店铺购买记录表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_refund_order
-- ----------------------------
DROP TABLE IF EXISTS `store_refund_order`;
CREATE TABLE `store_refund_order`  (
  `store_refund_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商城退款订单ID',
  `store_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城订单ID',
  `order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单号',
  `order_status` tinyint NULL DEFAULT 1 COMMENT '订单状态（1待付款 2待自提 3待发货 4待收货 5已完成 6退款售后 7已取消 8已关闭）',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户ID',
  `address_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户地址ID',
  `contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '所在地区(包含省市区街道)',
  `detail_address` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `longitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '经度',
  `latitude` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '纬度',
  `app_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'AppId',
  `pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付方式（APP微信 alipay_app支付宝 platform后台支付 free免费支付）',
  `pay_time` datetime NULL DEFAULT NULL COMMENT '支付时间',
  `trade_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付流水号',
  `remark` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单备注信息',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `refund_apply_time` datetime NULL DEFAULT NULL COMMENT '退款申请时间',
  `refund_audit_time` datetime NULL DEFAULT NULL COMMENT '退款审核时间',
  `refund_success_time` datetime NULL DEFAULT NULL COMMENT '退款成功时间',
  `refund_cause` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款原因',
  `refund_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '退款金额',
  `refund_explain` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款说明',
  `refund_url` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款照片',
  `refund_status` tinyint NULL DEFAULT 0 COMMENT '退款状态（0申请中 1已同意 2已拒绝 3已撤回）',
  `refuse_reason` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝退款原因',
  `total_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品总价',
  `delivery_price` decimal(10, 2) UNSIGNED NULL DEFAULT NULL COMMENT '配送费',
  `platform_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台优惠金额',
  `store_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '店铺优惠金额',
  `delivery_type` tinyint NULL DEFAULT 3 COMMENT '配送方式（1商家配送 2到店自取 3配送方式）',
  `pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '实付金额',
  `goods_num` int NULL DEFAULT NULL COMMENT '商品总数',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `store_contact_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺联系人',
  `store_contact_mobile` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺联系电话',
  `store_location` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺所在地区(包含省市区街道)',
  `store_detail_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺详细地址',
  `total_integral` decimal(10, 2) NULL DEFAULT NULL COMMENT '订单总积分',
  `receive_status` tinyint NULL DEFAULT 0 COMMENT '收货状态（0未收到货 1已收到货）',
  `logistics_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流公司名称',
  `logistics_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流公司编码',
  `logistics_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '物流单号',
  `remaining_pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '余额支付金额',
  `integral_deduct_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '积分抵扣金额',
  `pay_order_sn` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付订单号',
  `total_market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品出售总价',
  `before_refund_status` tinyint NULL DEFAULT 0 COMMENT '申请退款前的订单状态',
  `refund_type` tinyint NULL DEFAULT 1 COMMENT '退款类型（1仅退款 2退货退款）',
  `return_status` tinyint NULL DEFAULT -1 COMMENT '回寄状态（-1不需要回寄 0待寄出 1已寄出 2已收到）',
  `return_time` datetime NULL DEFAULT NULL COMMENT '回寄时间',
  `return_logistics_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '回寄物流公司名称',
  `return_logistics_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '回寄物流公司编码',
  `return_logistics_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '回寄物流单号',
  `return_picture` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '回寄照片',
  `receive_time` datetime NULL DEFAULT NULL COMMENT '收到时间',
  `goods_name` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '商品名称',
  `account_del_status` tinyint NULL DEFAULT 0 COMMENT '用户删除状态（0未删除 1已删除）',
  `store_del_status` tinyint NULL DEFAULT 0 COMMENT '商家删除状态（0未删除 1已删除）',
  `auto_audit_time` datetime NULL DEFAULT NULL COMMENT '退款自动审核时间',
  `order_type` tinyint NULL DEFAULT 1 COMMENT '订单类型（1普通订单 2批发订单 3消费金订单）',
  `project_id` bigint NULL DEFAULT NULL COMMENT '项目ID',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '原项目ID',
  PRIMARY KEY (`store_refund_order_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商城退款订单表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_refund_order_goods
-- ----------------------------
DROP TABLE IF EXISTS `store_refund_order_goods`;
CREATE TABLE `store_refund_order_goods`  (
  `store_refund_order_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商城退款订单商品ID',
  `store_refund_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城退款订单ID',
  `store_order_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城订单商品ID',
  `store_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商城订单ID',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `store_goods_spec_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `thumb` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '缩略图',
  `goods_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `goods_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品单价',
  `goods_num` int NULL DEFAULT 0 COMMENT '商品数量',
  `goods_total_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品总价',
  `order_status` tinyint NULL DEFAULT 1 COMMENT '订单状态（1待付款 2待自提 3待发货 4待收货 5已完成 6退款售后 7已取消 8已关闭）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `refund_apply_time` datetime NULL DEFAULT NULL COMMENT '退款申请时间',
  `refund_audit_time` datetime NULL DEFAULT NULL COMMENT '退款审核时间',
  `refund_success_time` datetime NULL DEFAULT NULL COMMENT '退款成功时间',
  `refund_cause` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款原因',
  `refund_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '退款金额',
  `refund_explain` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款说明',
  `refund_url` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '退款照片',
  `refund_status` tinyint NULL DEFAULT 0 COMMENT '退款状态（0申请中 1已同意 2已拒绝 3已撤回）',
  `refuse_reason` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝退款原因',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `platform_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '平台优惠金额',
  `store_coupon_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '店铺优惠金额',
  `pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '实付金额',
  `store_spec_name` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格名称',
  `before_refund_status` tinyint NULL DEFAULT 0 COMMENT '申请退款前的订单状态',
  `goods_integral` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品积分',
  `goods_total_integral` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品总积分',
  `remaining_pay_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '余额支付金额',
  `delivery_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '配送费',
  `market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品出售单价',
  `total_market_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '商品出售总价',
  `integral_deduct_price` decimal(10, 2) NULL DEFAULT NULL COMMENT '积分抵扣金额',
  `account_del_status` tinyint NULL DEFAULT 0 COMMENT '用户删除状态（0未删除 1已删除）',
  `store_del_status` tinyint NULL DEFAULT 0 COMMENT '商家删除状态（0未删除 1已删除）',
  `goods_type` tinyint NULL DEFAULT NULL COMMENT '商品类型（1现货 2期货）',
  `project_id` bigint NULL DEFAULT NULL COMMENT '项目ID',
  `original_project_id` bigint NULL DEFAULT NULL COMMENT '原项目ID',
  PRIMARY KEY (`store_refund_order_goods_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商城退款订单商品表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_search_records
-- ----------------------------
DROP TABLE IF EXISTS `store_search_records`;
CREATE TABLE `store_search_records`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `keyword` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `timestamp` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_user_time`(`user_id`, `timestamp`) USING BTREE,
  INDEX `idx_keyword`(`keyword`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_spec_item
-- ----------------------------
DROP TABLE IF EXISTS `store_spec_item`;
CREATE TABLE `store_spec_item`  (
  `store_spec_item_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品规格名称ID',
  `store_spec_type_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品规格ID',
  `spec_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格名称',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `sort_num` int NULL DEFAULT 0 COMMENT '顺序',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  PRIMARY KEY (`store_spec_item_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商品规格名称表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for store_spec_type
-- ----------------------------
DROP TABLE IF EXISTS `store_spec_type`;
CREATE TABLE `store_spec_type`  (
  `store_spec_type_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '商品规格类型ID',
  `spec_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '规格类型',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `sort_num` int NULL DEFAULT 0 COMMENT '顺序',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  PRIMARY KEY (`store_spec_type_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '商品规格类型表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for subjoin_price
-- ----------------------------
DROP TABLE IF EXISTS `subjoin_price`;
CREATE TABLE `subjoin_price`  (
  `subjoin_price_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '附加费用ID',
  `service_order_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '服务订单ID',
  `subjoin_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '附加金额',
  `type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '类型名称',
  `price_picture` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '费用图片',
  `pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '应付金额',
  `pay_status` tinyint NULL DEFAULT 0 COMMENT '支付状态（ 0：未支付,1：已支付）',
  `pay_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '支付方式（JSAPI=微信小程序支付,platform=后台支付,free=免费支付,APP=微信支付,alipay_app=支付宝支付）',
  `pay_time` datetime NULL DEFAULT NULL COMMENT '支付时间',
  `trade_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '支付流水号',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `order_sn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT 'order_sn',
  `payable_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '应付金额',
  `token_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '通证金额',
  `actual_pay_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '实际支付金额(拉起支付付款的金额)',
  `token_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '通证钱包ID',
  `cash_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '现金钱包ID',
  `ai_sync_order_status` tinyint NULL DEFAULT NULL COMMENT 'ai服务订单状态(0否 1是)',
  `cash_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '使用现金钱包总金额',
  `predict_token_price` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '通证金额',
  `token_transaction_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '通证消费交易单号',
  `enterprise_cash_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '企业现金收益',
  `enterprise_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '企业通证收益',
  `user_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '用户通证收益',
  `middle_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '中台通证收益',
  `invitation_token_profit` decimal(10, 2) NULL DEFAULT NULL COMMENT '邀请人通证收益',
  `reflow_token_amount` decimal(10, 2) NULL DEFAULT NULL COMMENT '回流通证',
  `commission_status` tinyint(1) NULL DEFAULT 0 COMMENT '分佣状态（0未分佣 1已分佣 2已到账）',
  PRIMARY KEY (`subjoin_price_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '附件费用' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for subscribe_time
-- ----------------------------
DROP TABLE IF EXISTS `subscribe_time`;
CREATE TABLE `subscribe_time`  (
  `subscribe_time_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '预约时间ID',
  `start_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '开始时间',
  `end_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '结束时间',
  `sort_num` int NULL DEFAULT 0 COMMENT '排序',
  `show_status` tinyint NULL DEFAULT 1 COMMENT '显示状态(0:不显示 1:显示)',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态(0:未删除 1:已删除)',
  PRIMARY KEY (`subscribe_time_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '预约时间' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for supplier_manage
-- ----------------------------
DROP TABLE IF EXISTS `supplier_manage`;
CREATE TABLE `supplier_manage`  (
  `supplier_manage_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '供应商管理id',
  `supplier_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商性质',
  `supplier_type_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '供应商性质id',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '单位名称',
  `paid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已付金额合计',
  `unpaid_money_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未付金额合计',
  `paid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '已开票金额',
  `unpaid_invoice_total` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '未开票金额',
  `contact_people` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系人',
  `contact_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `contact_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系地址',
  `tax_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '税号',
  `bank_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户银行',
  `bank_account` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '银行卡号',
  `category` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '类别',
  `remarks` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '是否删除(0:未删除 1:已删除)',
  `bank_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联行号',
  `esign_certification_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝认证状态(-1未认证 0认证中 1认证成功)',
  `esign_authorization_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝授权状态(-1未授权 0授权中 1授权成功)',
  `esign_authorization_deadline_time` datetime NULL DEFAULT NULL COMMENT 'e签宝授权截止日期',
  `auth_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '认证授权流程ID',
  `auth_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证授权长链接',
  `auth_short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证授权短链接',
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构账号ID',
  `core_status` tinyint NULL DEFAULT 0 COMMENT '核心状态(0否 1是)',
  `core_remarks` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '核心客户备注',
  `one_business_class_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '一级行业分类ID',
  `one_business_class_name` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '一级行业分类名称',
  `two_business_class_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '二级行业分类ID',
  `two_business_class_name` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '二级分类名称',
  `three_business_class_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '三级行业分类ID',
  `three_business_class_name` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '三年级行业分类名称',
  `province_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省编码',
  `province` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '省',
  `city_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市编码',
  `city` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '市',
  `county_code` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县编码',
  `county` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '区县',
  `customer_size_type` int NULL DEFAULT NULL COMMENT '客户规模(1微型企业 2小型企业 3中型企业 4大型企业)',
  `customer_type` int NULL DEFAULT 2 COMMENT '客户类型(1个人客户 2企业客户)',
  PRIMARY KEY (`supplier_manage_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '供应商管理表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_city
-- ----------------------------
DROP TABLE IF EXISTS `sys_city`;
CREATE TABLE `sys_city`  (
  `city_id` bigint NOT NULL AUTO_INCREMENT COMMENT '城市id',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父部门id',
  `ancestors` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '祖级列表',
  `city_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '城市名称',
  `order_num` int NULL DEFAULT 0 COMMENT '显示顺序',
  `leader` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '负责人',
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '邮箱',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '部门状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `city_level` tinyint NULL DEFAULT 0 COMMENT '城市等级(0:国家 1：省 2：市 3：区)',
  `adcode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '区行政编码',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '纬度',
  PRIMARY KEY (`city_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3729 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '城市表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_config
-- ----------------------------
DROP TABLE IF EXISTS `sys_config`;
CREATE TABLE `sys_config`  (
  `config_id` int NOT NULL AUTO_INCREMENT COMMENT '参数主键',
  `config_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '参数名称',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '参数键名',
  `config_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '参数键值',
  `config_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'N' COMMENT '系统内置（Y是 N否）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`config_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 100 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '参数配置表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_dept
-- ----------------------------
DROP TABLE IF EXISTS `sys_dept`;
CREATE TABLE `sys_dept`  (
  `dept_id` bigint NOT NULL AUTO_INCREMENT COMMENT '部门id',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父部门id',
  `ancestors` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '祖级列表',
  `dept_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '部门名称',
  `order_num` int NULL DEFAULT 0 COMMENT '显示顺序',
  `leader` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '负责人',
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '联系电话',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '邮箱',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '部门状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `dept_level` tinyint NULL DEFAULT 0 COMMENT '部门等级是否公司（0否:1:公司 ）',
  `county_coding` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '城市编码(废弃)',
  `weeks` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '周几，可以是多个',
  `holidays_status` tinyint NULL DEFAULT 1 COMMENT '0:否 1：节假日休息',
  `on_work` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业员工上班时间',
  `off_work` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '企业员工下班时间',
  `clocking_range` int NULL DEFAULT 0 COMMENT '企业员工打卡范围(米)',
  `clocking_score` int NULL DEFAULT 0 COMMENT '企业员工考勤打卡赠送积分',
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '打卡经度',
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '打卡维度',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '地址',
  `address_detail` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '详细地址',
  `reissue_num` int NULL DEFAULT 0 COMMENT '补卡次数',
  `fax` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '传真',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '网址',
  `open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户行',
  `open_bank_account` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '开户账号',
  `duty_paragraph` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '税号',
  `esign_certification_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝认证状态(-1未认证 0认证中 1认证成功)',
  `esign_authorization_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝授权状态(-1未授权 0授权中 1授权成功)',
  `esign_authorization_deadline_time` datetime NULL DEFAULT NULL COMMENT 'e签宝授权截止日期',
  `auth_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '授权流程ID',
  `auth_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构授权长链接',
  `auth_short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构授权短链接',
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构账号ID',
  `cer_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '认证流程ID',
  `cer_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证长链接',
  `cer_short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '机构认证短链接',
  `effective_time` datetime NULL DEFAULT NULL COMMENT '授权生效时间',
  `authorized_scopes` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '授权范围',
  `unified_social_credit_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '统一社会信用代码',
  PRIMARY KEY (`dept_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 219 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '部门表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_dict_data
-- ----------------------------
DROP TABLE IF EXISTS `sys_dict_data`;
CREATE TABLE `sys_dict_data`  (
  `dict_code` bigint NOT NULL AUTO_INCREMENT COMMENT '字典编码',
  `dict_sort` int NULL DEFAULT 0 COMMENT '字典排序',
  `dict_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '字典标签',
  `dict_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '字典键值',
  `dict_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '字典类型',
  `css_class` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '样式属性（其他样式扩展）',
  `list_class` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '表格回显样式',
  `is_default` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'N' COMMENT '是否默认（Y是 N否）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`dict_code`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 301 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '字典数据表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_dict_type
-- ----------------------------
DROP TABLE IF EXISTS `sys_dict_type`;
CREATE TABLE `sys_dict_type`  (
  `dict_id` bigint NOT NULL AUTO_INCREMENT COMMENT '字典主键',
  `dict_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '字典名称',
  `dict_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '字典类型',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`dict_id`) USING BTREE,
  UNIQUE INDEX `dict_type`(`dict_type`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 156 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '字典类型表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_job
-- ----------------------------
DROP TABLE IF EXISTS `sys_job`;
CREATE TABLE `sys_job`  (
  `job_id` bigint NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `job_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '任务名称',
  `job_group` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'DEFAULT' COMMENT '任务组名',
  `invoke_target` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '调用目标字符串',
  `cron_expression` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT 'cron执行表达式',
  `misfire_policy` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '3' COMMENT '计划执行错误策略（1立即执行 2执行一次 3放弃执行）',
  `concurrent` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '1' COMMENT '是否并发执行（0允许 1禁止）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '状态（0正常 1暂停）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '备注信息',
  PRIMARY KEY (`job_id`, `job_name`, `job_group`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 101 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '定时任务调度表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_job_log
-- ----------------------------
DROP TABLE IF EXISTS `sys_job_log`;
CREATE TABLE `sys_job_log`  (
  `job_log_id` bigint NOT NULL AUTO_INCREMENT COMMENT '任务日志ID',
  `job_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务名称',
  `job_group` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务组名',
  `invoke_target` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '调用目标字符串',
  `job_message` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '日志信息',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '执行状态（0正常 1失败）',
  `exception_info` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '异常信息',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`job_log_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '定时任务调度日志表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_logininfor
-- ----------------------------
DROP TABLE IF EXISTS `sys_logininfor`;
CREATE TABLE `sys_logininfor`  (
  `info_id` bigint NOT NULL AUTO_INCREMENT COMMENT '访问ID',
  `user_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户账号',
  `ipaddr` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '登录IP地址',
  `login_location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '登录地点',
  `browser` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '浏览器类型',
  `os` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '操作系统',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '登录状态（0成功 1失败）',
  `msg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '提示消息',
  `login_time` datetime NULL DEFAULT NULL COMMENT '访问时间',
  PRIMARY KEY (`info_id`) USING BTREE,
  INDEX `idx_sys_logininfor_s`(`status`) USING BTREE,
  INDEX `idx_sys_logininfor_lt`(`login_time`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1737 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '系统访问记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_menu
-- ----------------------------
DROP TABLE IF EXISTS `sys_menu`;
CREATE TABLE `sys_menu`  (
  `menu_id` bigint NOT NULL AUTO_INCREMENT COMMENT '菜单ID',
  `menu_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '菜单名称',
  `parent_id` bigint NULL DEFAULT 0 COMMENT '父菜单ID',
  `order_num` int NULL DEFAULT 0 COMMENT '显示顺序',
  `path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '路由地址',
  `component` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '组件路径',
  `query` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '路由参数',
  `route_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '路由名称',
  `is_frame` int NULL DEFAULT 1 COMMENT '是否为外链（0是 1否）',
  `is_cache` int NULL DEFAULT 0 COMMENT '是否缓存（0缓存 1不缓存）',
  `menu_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '菜单类型（M目录 C菜单 F按钮）',
  `visible` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '菜单状态（0显示 1隐藏）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '菜单状态（0正常 1停用）',
  `perms` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '权限标识',
  `icon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '#' COMMENT '菜单图标',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '备注',
  PRIMARY KEY (`menu_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2557 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '菜单权限表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_notice
-- ----------------------------
DROP TABLE IF EXISTS `sys_notice`;
CREATE TABLE `sys_notice`  (
  `notice_id` int NOT NULL AUTO_INCREMENT COMMENT '公告ID',
  `notice_title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '公告标题',
  `notice_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '公告类型（1通知 2公告）',
  `notice_content` longblob NULL COMMENT '公告内容',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '公告状态（0正常 1关闭）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`notice_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 11 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '通知公告表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_oper_log
-- ----------------------------
DROP TABLE IF EXISTS `sys_oper_log`;
CREATE TABLE `sys_oper_log`  (
  `oper_id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志主键',
  `title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '模块标题',
  `business_type` int NULL DEFAULT 0 COMMENT '业务类型（0其它 1新增 2修改 3删除）',
  `method` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '方法名称',
  `request_method` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '请求方式',
  `operator_type` int NULL DEFAULT 0 COMMENT '操作类别（0其它 1后台用户 2手机端用户）',
  `oper_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '操作人员',
  `dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '部门名称',
  `oper_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '请求URL',
  `oper_ip` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '主机地址',
  `oper_location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '操作地点',
  `oper_param` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '请求参数',
  `json_result` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '返回参数',
  `status` int NULL DEFAULT 0 COMMENT '操作状态（0正常 1异常）',
  `error_msg` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '错误消息',
  `oper_time` datetime NULL DEFAULT NULL COMMENT '操作时间',
  `cost_time` bigint NULL DEFAULT 0 COMMENT '消耗时间',
  PRIMARY KEY (`oper_id`) USING BTREE,
  INDEX `idx_sys_oper_log_bt`(`business_type`) USING BTREE,
  INDEX `idx_sys_oper_log_s`(`status`) USING BTREE,
  INDEX `idx_sys_oper_log_ot`(`oper_time`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5914 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '操作日志记录' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_post
-- ----------------------------
DROP TABLE IF EXISTS `sys_post`;
CREATE TABLE `sys_post`  (
  `post_id` bigint NOT NULL AUTO_INCREMENT COMMENT '岗位ID',
  `post_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '岗位编码',
  `post_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '岗位名称',
  `post_sort` int NOT NULL COMMENT '显示顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '状态（0正常 1停用）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`post_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '岗位信息表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_role
-- ----------------------------
DROP TABLE IF EXISTS `sys_role`;
CREATE TABLE `sys_role`  (
  `role_id` bigint NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色名称',
  `role_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色权限字符串',
  `role_sort` int NOT NULL COMMENT '显示顺序',
  `data_scope` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '1' COMMENT '数据范围（1：全部数据权限 2：自定数据权限 3：本部门数据权限 4：本部门及以下数据权限）',
  `menu_check_strictly` tinyint(1) NULL DEFAULT 1 COMMENT '菜单树选择项是否关联显示',
  `dept_check_strictly` tinyint(1) NULL DEFAULT 1 COMMENT '部门树选择项是否关联显示',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`role_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 108 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '角色信息表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_role_dept
-- ----------------------------
DROP TABLE IF EXISTS `sys_role_dept`;
CREATE TABLE `sys_role_dept`  (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `dept_id` bigint NOT NULL COMMENT '部门ID',
  PRIMARY KEY (`role_id`, `dept_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '角色和部门关联表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_role_menu
-- ----------------------------
DROP TABLE IF EXISTS `sys_role_menu`;
CREATE TABLE `sys_role_menu`  (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `menu_id` bigint NOT NULL COMMENT '菜单ID',
  PRIMARY KEY (`role_id`, `menu_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '角色和菜单关联表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_user
-- ----------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user`  (
  `user_id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `user_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户账号',
  `nick_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户昵称',
  `user_type` tinyint NULL DEFAULT 0 COMMENT '用户类型（1老板 2员工）',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户邮箱',
  `phonenumber` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '手机号码',
  `sex` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '用户性别（0男 1女 2未知）',
  `avatar` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '头像地址',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '密码',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '帐号状态（0正常 1停用）',
  `disable_end_date` datetime NULL DEFAULT NULL COMMENT '禁用截止日期',
  `disable_reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '禁用原因',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '0' COMMENT '删除标志（0代表存在 2代表删除）',
  `login_ip` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '最后登录IP',
  `login_date` datetime NULL DEFAULT NULL COMMENT '最后登录时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '创建者',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '更新者',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '备注',
  `company_id` bigint NULL DEFAULT 100 COMMENT '公司ID',
  `customer_service_status` tinyint NULL DEFAULT 0 COMMENT '客服状态(0否 1是)',
  `esign_certification_status` tinyint NULL DEFAULT -1 COMMENT 'e签宝认证状态(-1未认证 0认证中 1认证成功)',
  `auth_flow_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '认证授权流程ID',
  `auth_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '个人认证授权长链接',
  `auth_short_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '个人认证授权短链接',
  `psn_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '个人账号ID',
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 154 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户信息表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_user_post
-- ----------------------------
DROP TABLE IF EXISTS `sys_user_post`;
CREATE TABLE `sys_user_post`  (
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `post_id` bigint NOT NULL COMMENT '岗位ID',
  PRIMARY KEY (`user_id`, `post_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户与岗位关联表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for sys_user_role
-- ----------------------------
DROP TABLE IF EXISTS `sys_user_role`;
CREATE TABLE `sys_user_role`  (
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `role_id` bigint NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`user_id`, `role_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户和角色关联表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for token_wallet
-- ----------------------------
DROP TABLE IF EXISTS `token_wallet`;
CREATE TABLE `token_wallet`  (
  `token_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '通证钱包ID',
  `account_type` tinyint(1) NULL DEFAULT NULL COMMENT '用户类型（1用户 2企业）',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户ID',
  `customer_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '客户ID',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户名称',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `total_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '总收益',
  `remaining_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '余额',
  `withdrawal_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `frozen_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '冻结金额',
  `wait_entry_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '待入账金额',
  `wallet_status` tinyint(1) NULL DEFAULT 0 COMMENT '钱包状态（0正常 1冻结 2禁用）',
  `del_status` tinyint(1) NULL DEFAULT 0 COMMENT '删除状态（0未删除 1已删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`token_wallet_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '通证钱包表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for token_wallet_transaction
-- ----------------------------
DROP TABLE IF EXISTS `token_wallet_transaction`;
CREATE TABLE `token_wallet_transaction`  (
  `token_wallet_transaction_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '通证钱包交易流水ID',
  `token_wallet_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '通证钱包ID',
  `account_type` tinyint(1) NULL DEFAULT NULL COMMENT '用户类型（1用户 2企业）',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户ID',
  `customer_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '客户ID',
  `source_customer_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '来源客户ID',
  `account_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户名称',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `transaction_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '交易单号',
  `transaction_type` tinyint NULL DEFAULT NULL COMMENT '交易类型（1充值 2消费扣款 3退款 4提现 5冻结 6解冻 7奖励 8扣罚 9待入账 10入账 11转账转出 12转账转入）',
  `income_expense_type` tinyint(1) NULL DEFAULT NULL COMMENT '收入或支出（1-收入 2-支出）',
  `transaction_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '交易名称',
  `amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易金额',
  `before_remaining_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前余额（对应 remaining_amount）',
  `after_remaining_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后余额（对应 remaining_amount）',
  `before_frozen_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前冻结金额（对应 frozen_amount）',
  `after_frozen_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后冻结金额（对应 frozen_amount）',
  `before_wait_entry_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前待入账金额（对应 wait_entry_amount）',
  `after_wait_entry_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后待入账金额（对应 wait_entry_amount）',
  `before_total_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易前总收益（对应 total_amount）',
  `after_total_amount` decimal(18, 2) NULL DEFAULT 0.00 COMMENT '交易后总收益（对应 total_amount）',
  `related_biz_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '关联业务单号（如订单号、退款单号等）',
  `related_biz_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '关联业务类型（order订单 refund退款 withdraw提现 transfer转账）',
  `order_type` tinyint NULL DEFAULT NULL COMMENT '订单类型（1商城订单）',
  `transaction_status` tinyint(1) NULL DEFAULT 0 COMMENT '交易状态（0待处理 1成功 2失败 3撤销）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '交易备注',
  `source_trace_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '资金来源链路JSON（冗余字段，便于快速查询）',
  `target_trace_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '资金去向链路JSON（冗余字段，便于快速查询）',
  `transaction_time` datetime NULL DEFAULT NULL COMMENT '交易完成时间',
  `source_app_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '来源APP名称',
  `source_app_logo` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '来源APPlogo',
  `transaction_detail` json NULL COMMENT '交易详情',
  `operator` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '操作人',
  `operator_id` bigint NULL DEFAULT NULL COMMENT '操作人ID',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '创建人',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`token_wallet_transaction_id`) USING BTREE,
  INDEX `idx_token_wallet_id`(`token_wallet_id`) USING BTREE COMMENT '通证钱包ID索引',
  INDEX `idx_global_account_id`(`account_id`) USING BTREE COMMENT '全局用户ID索引',
  INDEX `idx_customer_id`(`customer_id`) USING BTREE COMMENT '客户ID索引',
  INDEX `idx_account_type`(`account_type`) USING BTREE COMMENT '用户类型索引',
  INDEX `idx_transaction_type`(`transaction_type`) USING BTREE COMMENT '交易类型索引',
  INDEX `idx_transaction_status`(`transaction_status`) USING BTREE COMMENT '交易状态索引',
  INDEX `idx_related_biz_no`(`related_biz_no`) USING BTREE COMMENT '关联业务单号索引',
  INDEX `idx_create_time`(`create_time`) USING BTREE COMMENT '创建时间索引',
  INDEX `idx_transaction_time`(`transaction_time`) USING BTREE COMMENT '交易时间索引',
  INDEX `idx_wallet_type_status`(`token_wallet_id`, `transaction_type`, `transaction_status`) USING BTREE COMMENT '钱包-类型-状态联合索引',
  INDEX `idx_account_create_time`(`account_id`, `create_time`) USING BTREE COMMENT '用户-创建时间联合索引',
  INDEX `idx_customer_create_time`(`customer_id`, `create_time`) USING BTREE COMMENT '客户-创建时间联合索引',
  INDEX `idx_transaction_no`(`transaction_no`) USING BTREE COMMENT '交易单号唯一索引'
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '通证钱包交易流水表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for user_clocking
-- ----------------------------
DROP TABLE IF EXISTS `user_clocking`;
CREATE TABLE `user_clocking`  (
  `user_clocking_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户考勤ID',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `user_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户姓名',
  `user_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户手机号',
  `user_head` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户头像',
  `clocking_date` date NULL DEFAULT NULL COMMENT '打卡日期',
  `clocking_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '上班打卡地点',
  `on_work_time` datetime NULL DEFAULT NULL COMMENT '上班打卡时间/签到时间',
  `off_work_time` datetime NULL DEFAULT NULL COMMENT '下班打卡时间',
  `clocking_type` tinyint NULL DEFAULT 0 COMMENT '上班打卡类型 0：未打卡 1：正常打卡 2：外勤打卡',
  `clocking_status` tinyint NULL DEFAULT 0 COMMENT '上班打卡状态 0：未打卡 1：正常 2：迟到 3：早退  5：旷工 6：补卡 7请假',
  `off_clocking_address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '下班打卡地点',
  `off_clocking_type` tinyint NULL DEFAULT 0 COMMENT '下班打卡类型  0：未打卡 1：正常打卡 2：外勤打卡',
  `off_clocking_status` tinyint NULL DEFAULT 0 COMMENT '下班打卡状态 0：未打卡 1：正常 2：迟到 3：早退 5：旷工 6：补卡 7请假',
  `pics` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '上班外出签到图片',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '上班外出签到备注',
  `off_clocking_pics` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '下班外出签到图片',
  `off_clocking_remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '下班外出签到备注',
  `clocking_score` int NULL DEFAULT 0 COMMENT '考勤打卡/外出签到赠送积分 废弃',
  `company_id` bigint NULL DEFAULT NULL COMMENT '公司ID',
  `company_name` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '公司名称',
  `dept_id` bigint NULL DEFAULT NULL COMMENT '部门ID',
  `dept_names` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '部门名称',
  `post_ids` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '岗位IDS',
  `post_name` varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '岗位名称s',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态 0:未删除  1:已删除',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`user_clocking_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '用户考勤表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for user_menu_config
-- ----------------------------
DROP TABLE IF EXISTS `user_menu_config`;
CREATE TABLE `user_menu_config`  (
  `user_menu_config_id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户菜单配置表',
  `user_id` bigint NULL DEFAULT NULL COMMENT '用户ID',
  `permission` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '菜单布局数据',
  `config_version` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '配置版本号',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `menu_order` int NULL DEFAULT NULL COMMENT '菜单排序',
  `is_enabled` int NULL DEFAULT NULL COMMENT '是否启用(0否 1是)',
  PRIMARY KEY (`user_menu_config_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 18 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户菜单配置表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for video
-- ----------------------------
DROP TABLE IF EXISTS `video`;
CREATE TABLE `video`  (
  `video_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '视频id',
  `video_class_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '1' COMMENT '视频分类',
  `video_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '视频路径',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '用户id',
  `store_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺ID',
  `store_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '店铺名称',
  `store_goods_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品ID',
  `goods_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '商品名称',
  `browse_number` int NULL DEFAULT 0 COMMENT '浏览数量',
  `comment_number` int NULL DEFAULT 0 COMMENT '评论数量',
  `like_number` int NULL DEFAULT 0 COMMENT '点赞数量',
  `collect_number` int NULL DEFAULT 0 COMMENT '收藏数量',
  `video_audit_status` tinyint NULL DEFAULT 0 COMMENT '视频审核状态（0审核中 1已通过 2已拒绝）',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '更新时间',
  `video_title` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '视频标题',
  `two_store_class_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '平台二级分类ID',
  `refuse_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '审核拒绝原因',
  `drafts_status` tinyint NULL DEFAULT 0 COMMENT '是否草稿箱 0否 1是',
  `show_status` tinyint NULL DEFAULT 1 COMMENT '是否显示 0否 1是',
  `bid_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '招标记录id',
  `video_source` tinyint NULL DEFAULT 1 COMMENT '视频来源(1:管理员端 2用户端)',
  `good_type` tinyint NULL DEFAULT 1 COMMENT '挂载商品类型（1商城商品 2服务）',
  `primary_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '主键id',
  PRIMARY KEY (`video_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '视频表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for withdrawal_account
-- ----------------------------
DROP TABLE IF EXISTS `withdrawal_account`;
CREATE TABLE `withdrawal_account`  (
  `withdrawal_account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '提现账户ID',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `account_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '账户类型（JSAPI=微信小程序,,APP=微信,alipay_app=支付宝）',
  `account_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '账户账号',
  `real_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提现姓名',
  `real_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提现手机号',
  `default_status` tinyint NULL DEFAULT 0 COMMENT '是否默认（0：否 1：是）',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  PRIMARY KEY (`withdrawal_account_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '提现账户' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for withdrawal_record
-- ----------------------------
DROP TABLE IF EXISTS `withdrawal_record`;
CREATE TABLE `withdrawal_record`  (
  `withdrawal_record_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户提现记录ID',
  `order_sn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '订单编号',
  `attestation_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '认证ID',
  `account_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '用户ID',
  `account_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '账户账号',
  `account_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT '' COMMENT '账户类型（JSAPI=微信小程序,,APP=微信,alipay_app=支付宝）',
  `real_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提现姓名',
  `real_phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提现手机号',
  `withdrawal_price` decimal(20, 2) NULL DEFAULT 0.00 COMMENT '提现金额',
  `service_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '提现手续费',
  `withdraw_price` decimal(20, 2) NULL DEFAULT NULL COMMENT '到账金额',
  `apply_time` datetime NULL DEFAULT NULL COMMENT '申请时间',
  `payment_time` datetime NULL DEFAULT NULL COMMENT '到账时间',
  `audit_status` tinyint NULL DEFAULT 0 COMMENT '审核状态（0=待审核 1=转账中 2=已提现 3：已拒绝）',
  `offline_status` tinyint NULL DEFAULT 0 COMMENT '线下状态（0:否 1:下线转账）',
  `app_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'appId',
  `batch_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信批次单号',
  `detail_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '微信明细单的唯一标识',
  `out_biz_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '支付宝提现商家侧唯一订单号，由商家自定义',
  `reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '拒绝理由',
  `create_time` datetime NULL DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT NULL COMMENT '修改时间',
  `del_status` tinyint NULL DEFAULT 0 COMMENT '删除状态（0正常 1删除）',
  PRIMARY KEY (`withdrawal_record_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '提现记录' ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
