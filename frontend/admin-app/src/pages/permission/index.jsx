import React from 'react'

function PermissionPage() {
  return (
    <div>
      <h2>权限管理</h2>
      <div className="card">
        <h3>当前状态</h3>
        <p>权限管理页面已补齐，当前后端尚未提供管理员、角色和权限接口。</p>
        <p>后续可在这里接入登录账号、角色分配、菜单权限和接口权限配置。</p>
      </div>
      <div className="card">
        <h3>建议权限模块</h3>
        <table>
          <thead>
            <tr>
              <th>模块</th>
              <th>说明</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>管理员账号</td>
              <td>维护后台用户基本信息</td>
              <td>待实现</td>
            </tr>
            <tr>
              <td>角色管理</td>
              <td>配置管理员、运营、讲解员等角色</td>
              <td>待实现</td>
            </tr>
            <tr>
              <td>权限分配</td>
              <td>控制菜单访问和操作权限</td>
              <td>待实现</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default PermissionPage
