"""
Git提交前清理脚本
递归扫描项目所有文件夹，删除：
1. 所有 __pycache__ 文件夹（Python字节码缓存）
2. 所有 logs 文件夹（日志文件）
3. 所有 sqlite 文件夹（数据库文件）

使用方法：
在项目根目录运行：python 提交git前运行.py
"""
import os
import shutil
import stat
import time


def force_remove_readonly(func, path, exc_info):
    """
    强制删除只读文件的错误处理函数
    当文件是只读时，修改权限后重试删除
    """
    if not os.access(path, os.W_OK):
        # 修改文件权限为可写
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
        func(path)
    else:
        raise


def delete_all_folders_by_name(root_dir, folder_names, retry=3):
    """
    递归删除所有指定名称的文件夹
    
    参数：
        root_dir: 根目录
        folder_names: 要删除的文件夹名称列表
        retry: 重试次数（默认3次）
    
    返回：
        deleted_paths: 已删除的文件夹路径列表
    """
    deleted_paths = []
    folders_to_delete = []
    
    # 第一步：遍历查找所有匹配的文件夹
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        for dirname in dirnames:
            if dirname in folder_names:
                folder_path = os.path.join(dirpath, dirname)
                folders_to_delete.append(folder_path)
    
    # 第二步：删除找到的文件夹
    for folder_path in folders_to_delete:
        deleted = False
        for attempt in range(retry):
            try:
                # 使用 onerror 参数处理只读文件
                shutil.rmtree(folder_path, onerror=force_remove_readonly)
                deleted_paths.append(folder_path)
                print(f"✓ 已删除: {folder_path}")
                deleted = True
                break
            except PermissionError:
                if attempt < retry - 1:
                    print(f"⚠ 文件被占用，等待1秒后重试... (尝试 {attempt + 1}/{retry})")
                    print(f"  文件夹: {folder_path}")
                    time.sleep(1)
                else:
                    print(f"✗ 删除失败: {folder_path}")
                    print(f"  错误: 文件可能被其他程序占用")
                    print(f"  建议: 关闭占用该文件的程序后重试")
            except Exception as e:
                print(f"✗ 删除失败: {folder_path}")
                print(f"  错误: {e}")
                break
    
    return deleted_paths


def clean_all():
    """清理所有缓存和运行时文件"""
    print("="*70)
    print("Git提交前清理脚本 - 递归扫描整个项目")
    print("="*70)
    print(f"扫描目录: {os.path.abspath('.')}")
    print()
    
    total_deleted = 0
    
    # 1. 清理 __pycache__
    print("="*70)
    print("【1/3】清理 __pycache__ 文件夹（Python字节码缓存）")
    print("="*70)
    pycache_paths = delete_all_folders_by_name(".", ["__pycache__"])
    if pycache_paths:
        print(f"\n✓ 共删除 {len(pycache_paths)} 个 __pycache__ 文件夹")
        total_deleted += len(pycache_paths)
    else:
        print("\n- 未找到任何 __pycache__ 文件夹")
    
    # 2. 清理 logs 文件夹
    print("\n" + "="*70)
    print("【2/3】清理 logs 文件夹（日志文件）")
    print("="*70)
    logs_paths = delete_all_folders_by_name(".", ["logs"])
    if logs_paths:
        print(f"\n✓ 共删除 {len(logs_paths)} 个 logs 文件夹")
        total_deleted += len(logs_paths)
    else:
        print("\n- 未找到任何 logs 文件夹")
    
    # 3. 清理 sqlite 文件夹
    print("\n" + "="*70)
    print("【3/3】清理 sqlite 文件夹（数据库文件）")
    print("="*70)
    sqlite_paths = delete_all_folders_by_name(".", ["sqlite"])
    if sqlite_paths:
        print(f"\n✓ 共删除 {len(sqlite_paths)} 个 sqlite 文件夹")
        total_deleted += len(sqlite_paths)
    else:
        print("\n- 未找到任何 sqlite 文件夹")
    
    # 总结
    print("\n" + "="*70)
    print(f"✓ 清理完成！共删除 {total_deleted} 个文件夹")
    print("="*70)
    print("\n📋 清理说明：")
    print("  - __pycache__: Python字节码缓存，会自动重新生成")
    print("  - logs: 应用运行日志，会在程序运行时自动创建")
    print("  - sqlite: 数据库文件，会在程序运行时自动创建")
    print("\n💡 提示：")
    print("  这些文件都会在程序运行时自动重新生成。")
    print("  提交到Git仓库前运行此脚本可以保持项目干净。")
    print()


if __name__ == "__main__":
    clean_all()
