<template>
  <div class="not-found">
    <h1>404</h1>
    <p>抱歉，您访问的页面不存在</p>
    <el-button type="primary" @click="$router.push('/dashboard/index')">返回工作台</el-button>
  </div>
</template>

<script setup></script>

<style lang="scss" scoped>
.not-found {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  h1 {
    font-size: 80px;
    margin: 0;
    color: $primary-color;
  }
  p {
    color: #8a919f;
  }
}
</style>
