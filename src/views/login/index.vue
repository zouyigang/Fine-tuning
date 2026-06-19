<template>
  <div class="login-page">
    <div class="login-box">
      <div class="brand">
        <div class="logo">
          <el-icon :size="30"><MagicStick /></el-icon>
        </div>
        <h1>模型微调通用平台</h1>
        <p>面向公安业务场景的大模型微调与管理平台</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" class="submit-btn" :loading="loading" @click="submit">登 录</el-button>
      </el-form>

      <el-alert class="demo-tip" type="info" :closable="false" show-icon>
        <template #title>
          演示账号：<b>admin / admin123</b>（系统管理员）、<b>analyst / 123456</b>（算法工程师）
        </template>
      </el-alert>
    </div>
    <div class="copyright">© 2026 模型微调通用平台 · 系统原型</div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Lock, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function submit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await userStore.login({ ...form })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/dashboard/index'
    router.push(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a8a 0%, #2f54eb 50%, #13c2c2 100%);
  position: relative;
}

.login-box {
  width: 400px;
  padding: 40px 36px 28px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

.brand {
  text-align: center;
  margin-bottom: 28px;

  .logo {
    width: 60px;
    height: 60px;
    margin: 0 auto 12px;
    border-radius: 14px;
    background: linear-gradient(135deg, #2f54eb, #13c2c2);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  h1 {
    font-size: 21px;
    font-weight: 700;
    color: #1f2733;
    margin: 0 0 6px;
  }
  p {
    font-size: 12px;
    color: #8a919f;
    margin: 0;
  }
}

.submit-btn {
  width: 100%;
  margin-top: 6px;
  letter-spacing: 4px;
}

.demo-tip {
  margin-top: 18px;
}

.copyright {
  position: absolute;
  bottom: 24px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
}
</style>
