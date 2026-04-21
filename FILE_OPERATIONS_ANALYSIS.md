# AIGI-Holmes 文件操作风险分析

**报告日期**: 2026-04-09  
**分析范围**: 跨驱动器文件移动/重命名、权限问题、文件锁定

---

## 🚨 关键发现：错误代码5（ACCESS_DENIED）的根本原因

Windows ERROR_5 (ACCESS_DENIED) 通常由以下原因引起：
1. **跨驱动器移动** - `shutil.move()` 在跨驱动器时会尝试先复制再删除，删除时可能因权限失败
2. **文件被占用** - 杀毒软件、防护软件、编辑器等可能锁定文件
3. **父目录权限不足** - 某些临时目录权限限制
4. **frozen/executable模式** - PyInstaller封装的EXE可能在沙箱环境运行
5. **并发操作** - 多个进程同时操作同一文件

---

## ⚠️ 发现的所有可疑代码片段

### 1. ❌ **[高风险] swift/hub/utils/caching.py - 跨驱动器临时文件移动**

**文件**: [swift/hub/utils/caching.py](swift/hub/utils/caching.py#L48)  
**行号**: 48  
**问题**: 使用 `move()` 从系统临时目录移动到缓存目录，可能跨驱动器

```python
def save_cached_files(self):
    """Save cache metadata."""
    # save new meta to tmp and move to KEY_FILE_NAME
    cache_keys_file_path = os.path.join(self.cache_root_location, FileSystemCache.KEY_FILE_NAME)
    # TODO: Sync file write
    fd, fn = tempfile.mkstemp()
    with open(fd, 'wb') as f:
        pickle.dump(self.cached_files, f)
    move(fn, cache_keys_file_path)  # ⚠️ 可能跨驱动器！
```

**风险类型**:
- ✗ 跨驱动器移动失败
- ✗ 临时文件权限问题
- ✗ 缓存目录权限不足

**建议修复**:
```python
def save_cached_files(self):
    cache_keys_file_path = os.path.join(self.cache_root_location, FileSystemCache.KEY_FILE_NAME)
    fd, fn = tempfile.mkstemp(dir=self.cache_root_location)  # 在同驱动器创建临时文件
    try:
        with os.fdopen(fd, 'wb') as f:
            pickle.dump(self.cached_files, f)
        # 使用 os.replace() 而不是 shutil.move()
        os.replace(fn, cache_keys_file_path)
    except Exception:
        if os.path.exists(fn):
            try:
                os.remove(fn)
            except Exception:
                pass
        raise
```

---

### 2. ❌ **[高风险] swift/tuners/base.py - 模型文件移动**

**文件**: [swift/tuners/base.py](swift/tuners/base.py#L809)  
**行号**: 809  
**问题**: 使用 `shutil.move()` 移动模型配置文件

```python
if 'default' in adapter_names:
    shutil.move(
        os.path.join(output_dir, 'default', CONFIG_NAME),  # 源路径
        os.path.join(output_dir, CONFIG_NAME)               # 目标路径
    )
    state_dict = SwiftModel.load_state_file(os.path.join(output_dir, 'default'))
    safe_serialization = os.path.isfile(os.path.join(output_dir, 'default', SAFETENSORS_WEIGHTS_NAME))
    SwiftModel._save_state_dict(state_dict, output_dir, safe_serialization)
    shutil.rmtree(os.path.join(output_dir, 'default'))  # ⚠️ 权限问题！
```

**风险类型**:
- ✗ 文件被模型后继流程使用，导致移动失败
- ✗ rmtree 权限不足

**建议修复**:
```python
if 'default' in adapter_names:
    src_config = os.path.join(output_dir, 'default', CONFIG_NAME)
    dst_config = os.path.join(output_dir, CONFIG_NAME)
    try:
        # 先复制，启用覆盖
        shutil.copy2(src_config, dst_config)
    except Exception as e:
        logger.error(f"Failed to copy config: {e}")
        # 备选：直接读写
        with open(src_config, 'r') as src:
            with open(dst_config, 'w') as dst:
                dst.write(src.read())
    
    state_dict = SwiftModel.load_state_file(os.path.join(output_dir, 'default'))
    safe_serialization = os.path.isfile(os.path.join(output_dir, 'default', SAFETENSORS_WEIGHTS_NAME))
    SwiftModel._save_state_dict(state_dict, output_dir, safe_serialization)
    
    # 安全删除目录
    try:
        shutil.rmtree(os.path.join(output_dir, 'default'), ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to remove default folder: {e}")
```

---

### 3. ⚠️ **[中风险] backend/routers/detect.py - 临时目录清理**

**文件**: [backend/routers/detect.py](backend/routers/detect.py#L819)  
**行号**: 785, 819, 822  
**问题**: 创建临时目录用于ZIP打包，但清理可能失败

```python
@router.get("/images/batch-download")
async def api_batch_download_images(urls: str = Query(..., min_length=1)):
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()  # ⚠️ 系统临时目录可能权限受限
    zip_path = os.path.join(temp_dir, zip_filename)
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # ... 写入图片
            pass
        
        return FileResponse(zip_path, ...)  # ⚠️ 文件仍被占用！
    
    except ImageFormatError:
        shutil.rmtree(temp_dir, ignore_errors=True)  # 可能失败
        raise
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)  # 可能失败
        raise ImageFormatError(f"批量下载失败：{str(e)}")
    
    # ❗ 关键问题：函数返回后，temp_dir 中的 ZIP 文件仍被 FastAPI 读取！
    #    Windows 会锁定该文件，导致清理失败。
```

**风险类型**:
- ✗ 临时目录未及时清理（临时文件泄露）
- ✗ FileResponse 仍在读取文件时试图删除
- ✗ 杀毒软件可能扫描临时文件

**建议修复**:
```python
@router.get("/images/batch-download")
async def api_batch_download_images(urls: str = Query(..., min_length=1)):
    from fastapi.responses import StreamingResponse
    import io
    
    # ✅ 完全在内存中构建 ZIP，不使用临时磁盘文件
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            success_count = 0
            for i, url in enumerate(url_list, 1):
                try:
                    validate_public_url(url)
                    img = await async_download_image(url)
                    if img:
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        zf.writestr(f"image_{i:02d}.png", buf.getvalue())
                        success_count += 1
                except Exception as e:
                    logging.warning(f"Failed to download image {i}: {str(e)}")
        
        if success_count == 0:
            raise ImageFormatError("无法下载任何图片")
        
        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        raise ImageFormatError(f"批量下载失败：{str(e)}")
    finally:
        zip_buffer.close()  # 立即释放内存
```

---

### 4. ❌ **[高风险] swift/llm/utils/media.py - 资源文件移动**

**文件**: [swift/llm/utils/media.py](swift/llm/utils/media.py#L187)  
**行号**: 187-189  
**问题**: 下载解压后使用 `shutil.move()` 移动到目标目录，可能跨分区

```python
@staticmethod
def download(media_type, media_name):
    # ... 下载和解压逻辑 ...
    local_dirs = DownloadManager(...).download_and_extract(media_type)
    
    if is_not_compressed_file:
        shutil.move(str(local_dirs), final_path)     # ⚠️ 可能跨驱动器！
    else:
        shutil.move(str(local_dirs), final_folder)   # ⚠️ 可能跨驱动器！
    
    return final_folder
```

**风险类型**:
- ✗ 跨驱动器移动会 DELETE 源文件，权限不足则失败
- ✗ 目标目录可能在网络驱动器
- ✗ 杀毒软件可能阻止删除

**建议修复**:
```python
@staticmethod
def download(media_type, media_name):
    local_dirs = DownloadManager(...).download_and_extract(media_type)
    
    try:
        if is_not_compressed_file:
            # 尝试 move，失败则 copy + rmtree
            try:
                shutil.move(str(local_dirs), final_path)
            except (OSError, PermissionError) as e:
                logger.warning(f"shutil.move failed: {e}, falling back to copy+delete")
                shutil.copy2(str(local_dirs), final_path)
                shutil.rmtree(str(local_dirs), ignore_errors=True)
        else:
            try:
                shutil.move(str(local_dirs), final_folder)
            except (OSError, PermissionError) as e:
                logger.warning(f"shutil.move failed: {e}, falling back to copytree+delete")
                shutil.copytree(str(local_dirs), final_folder, dirs_exist_ok=True)
                shutil.rmtree(str(local_dirs), ignore_errors=True)
    except Exception as e:
        logger.error(f"Failed to move media resources: {e}")
        raise
    
    return final_folder
```

---

### 5. ⚠️ **[中风险] swift/hub/file_download.py - 文件替换**

**文件**: [swift/hub/file_download.py](swift/hub/file_download.py#L284)  
**行号**: 284-290  
**问题**: 下载文件后使用 `os.replace()` 完成操作，但可能因权限或文件锁定失败

```python
def http_get_file(...):
    temp_file_manager = partial(tempfile.NamedTemporaryFile, mode='wb', dir=local_dir, delete=False)
    with temp_file_manager() as temp_file:
        # ... 下载内容 ...
        pass
    
    downloaded_length = os.path.getsize(temp_file.name)
    if total != downloaded_length:
        os.remove(temp_file.name)  # ⚠️ 可能因权限失败
        msg = f'File download incomplete: {total} vs {downloaded_length}'
        raise FileDownloadError(msg)
    
    os.replace(temp_file.name, os.path.join(local_dir, file_name))  # ⚠️ 可能原子操作失败
```

**风险类型**:
- ✗ 不完整下载时无法删除临时文件
- ✗ os.replace() 在文件被占用时失败
- ✗ 临时文件堆积

**建议修复**:
```python
def http_get_file(...):
    temp_file_manager = partial(tempfile.NamedTemporaryFile, mode='wb', dir=local_dir, delete=False)
    temp_file = None
    try:
        with temp_file_manager() as temp_file:
            temp_file_name = temp_file.name
            # ... 下载内容 ...
        
        downloaded_length = os.path.getsize(temp_file_name)
        if total != downloaded_length:
            raise FileDownloadError(f'File download incomplete: {total} vs {downloaded_length}')
        
        # 使用 os.replace() 原子操作
        target_path = os.path.join(local_dir, file_name)
        os.replace(temp_file_name, target_path)
        
    except Exception as e:
        # 确保清理临时文件
        if temp_file and hasattr(temp_file, 'name'):
            try:
                os.remove(temp_file.name)
            except Exception:
                pass
        raise
```

---

### 6. ⚠️ **[中风险] pyi_rthook_cwd.py - 环境文件复制**

**文件**: [pyi_rthook_cwd.py](pyi_rthook_cwd.py#L45)  
**行号**: 45  
**问题**: PyInstaller 运行时抄本尝试复制 .env 文件，在 frozen 模式下可能失败

```python
if getattr(sys, 'frozen', False):
    _env_path = _exe_dir / '.env'
    _env_example = Path(_meipass) / '.env.example' if _meipass else None
    if _env_path and not _env_path.exists() and _env_example and _env_example.exists():
        try:
            import shutil
            shutil.copy(_env_example, _env_path)  # ⚠️ 权限问题！
        except Exception as _e:
            print(f"[RTHOOK] WARNING: Failed to copy .env.example -> .env: {_e}", flush=True)
```

**风险类型**:
- ✗ EXE 目录可能是只读的或系统保护路径
- ✗ frozen 模式下用户权限受限
- ✗ 杀毒软件可能拦截

**建议修复**:
```python
if getattr(sys, 'frozen', False):
    _env_path = _exe_dir / '.env'
    _env_example = Path(_meipass) / '.env.example' if _meipass else None
    
    if _env_path and not _env_path.exists() and _env_example and _env_example.exists():
        try:
            # 使用写权限打开
            os.makedirs(_exe_dir, exist_ok=True)
            with open(_env_example, 'r', encoding='utf-8') as src:
                with open(_env_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            # 设置权限
            try:
                os.chmod(_env_path, 0o644)
            except Exception:
                pass
        except Exception as _e:
            # 不能放在 EXE 目录，尝试用户主目录
            try:
                user_env = Path.home() / '.aigi-holmes' / '.env'
                user_env.parent.mkdir(parents=True, exist_ok=True)
                with open(_env_example, 'r', encoding='utf-8') as src:
                    with open(user_env, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                print(f"[RTHOOK] .env created at {user_env}", flush=True)
            except Exception as _e2:
                print(f"[RTHOOK] WARNING: Failed to copy .env: {_e2}", flush=True)
```

---

### 7. ⚠️ **[中风险] scripts/benchmark/exp_utils.py - 路径拼接错误**

**文件**: [scripts/benchmark/exp_utils.py](scripts/benchmark/exp_utils.py#L302)  
**行号**: 302  
**问题**: 路径拼接逻辑可能导致目标路径不存在

```python
@staticmethod
def _get_metric(exp: Experiment):
    path = os.path.join(ckpt_dir, f'{ckpt_name}-merged')
    if os.path.exists(path):
        shutil.rmtree(exp.name, ignore_errors=True)
        os.makedirs(exp.name, exist_ok=True)
        shutil.move(path, os.path.join(exp.name, path))  # ⚠️ 逻辑错误！
        return {'best_model_checkpoint': os.path.join(exp.name, path)}
```

**问题分析**:
```
path = "/home/user/ckpt/model-merged"
exp.name = "exp_001"

目标 = os.path.join("exp_001", "/home/user/ckpt/model-merged")
     = "/home/user/ckpt/model-merged"  # 绝对路径覆盖 exp.name！
```

**建议修复**:
```python
@staticmethod
def _get_metric(exp: Experiment):
    path = os.path.join(ckpt_dir, f'{ckpt_name}-merged')
    if os.path.exists(path):
        os.makedirs(exp.name, exist_ok=True)
        # 只移动文件夹名称，不包含完整路径
        dst_path = os.path.join(exp.name, os.path.basename(path))
        try:
            shutil.move(path, dst_path)
        except Exception as e:
            logger.error(f"Failed to move checkpoint: {e}")
            # 备选方案
            shutil.copytree(path, dst_path, dirs_exist_ok=True)
            shutil.rmtree(path, ignore_errors=True)
        
        return {'best_model_checkpoint': dst_path}
```

---

### 8. ⚠️ **[低风险] swift/llm/megatron/utils.py - 文件重命名**

**文件**: [swift/llm/megatron/utils.py](swift/llm/megatron/utils.py#L43)  
**行号**: 43  
**问题**: 尝试重命名 qwen1.5 文件为 qwen1_5，但无异常处理完整性

```python
for fname in os.listdir(dir_path):
    old_path = os.path.join(dir_path, fname)
    new_path = os.path.join(dir_path, fname.replace('qwen1.', 'qwen1_'))
    if old_path != new_path:
        try:
            shutil.move(old_path, new_path)  # ⚠️ 可能因权限失败
        except FileNotFoundError:
            pass  # ❗ 只捕获 FileNotFoundError，忽略其他错误！
```

**风险类型**:
- ✗ 权限错误未处理
- ✗ 跨驱动器失败未处理
- ✗ 目录已存在时的冲突未处理

**建议修复**:
```python
for fname in os.listdir(dir_path):
    old_path = os.path.join(dir_path, fname)
    new_path = os.path.join(dir_path, fname.replace('qwen1.', 'qwen1_'))
    if old_path != new_path:
        try:
            shutil.move(old_path, new_path)
        except FileNotFoundError:
            pass
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to rename {fname}: {e}")
            # 尝试 os.rename() 作为备选
            try:
                os.rename(old_path, new_path)
            except Exception as e2:
                logger.error(f"Fallback rename also failed: {e2}")
```

---

### 9. ✅ **[已使用 os.replace()] swift/hub/file_download.py 的正确用法**

**文件**: [swift/hub/file_download.py](swift/hub/file_download.py#L290)  
**行号**: 290  
**优点**: 使用 `os.replace()` 而不是 `shutil.move()`

```python
os.replace(temp_file.name, os.path.join(local_dir, file_name))
```

**优势**:
- ✅ 原子操作（Windows）
- ✅ 跨驱动器不会问题
- ✅ 目标存在时安全覆盖

---

### 10. ⚠️ **[低风险] backend/routers/admin.py - 反馈数据下载**

**文件**: [backend/routers/admin.py](backend/routers/admin.py#L360)  
**行号**: 345-361  
**问题**: 下载反馈图片到本地目录，未处理并发和权限

```python
async def integrate_feedback_to_training(db: AsyncSession = Depends(get_db)):
    for fb in pending:
        try:
            if fb.image_url:
                label_dir = os.path.join("data", "feedback", fb.correct_label)
                os.makedirs(label_dir, exist_ok=True)
                filename = f"{fb.image_hash or fb.id}.jpg"
                filepath = os.path.join(label_dir, filename)
                if not os.path.exists(filepath):
                    await _download_to(fb.image_url, filepath)  # ⚠️ 并发下载可能冲突
            fb.used_in_training = 1
            integrated += 1
        except Exception:
            skipped += 1
```

**风险类型**:
- ✗ 并发下载时 TOCTOU（检查-使用）竞态
- ✗ 磁盘空间不足未处理
- ✗ 网络路径权限问题

**建议修复**:
```python
async def integrate_feedback_to_training(db: AsyncSession = Depends(get_db)):
    for fb in pending:
        try:
            if fb.image_url:
                label_dir = os.path.join("data", "feedback", fb.correct_label)
                os.makedirs(label_dir, exist_ok=True)
                filename = f"{fb.image_hash or fb.id}.jpg"
                filepath = os.path.join(label_dir, filename)
                
                # 使用临时文件 + 原子重命名
                temp_filepath = filepath + '.tmp'
                try:
                    await _download_to(fb.image_url, temp_filepath)
                    os.replace(temp_filepath, filepath)  # 原子操作
                except Exception:
                    if os.path.exists(temp_filepath):
                        try:
                            os.remove(temp_filepath)
                        except Exception:
                            pass
                    raise
            
            fb.used_in_training = 1
            integrated += 1
        except Exception as e:
            logger.warning(f"Failed to integrate feedback {fb.id}: {e}")
            skipped += 1
```

---

## 📊 总结表格

| 文件 | 行号 | 操作 | 风险等级 | 影响 | 状态 |
|------|------|------|---------|------|------|
| swift/hub/utils/caching.py | 48 | shutil.move() | ❌ 高 | 跨驱动器失败 | 需修复 |
| swift/tuners/base.py | 809 | shutil.move() | ❌ 高 | 权限不足 | 需修复 |
| backend/routers/detect.py | 785-822 | shutil.rmtree() | ⚠️ 中 | 临时文件泄露 | 需修复 |
| swift/llm/utils/media.py | 187-189 | shutil.move() | ❌ 高 | 跨驱动器失败 | 需修复 |
| swift/hub/file_download.py | 284-290 | os.remove()/os.replace() | ⚠️ 中 | 权限失败 | 部分良好 |
| pyi_rthook_cwd.py | 45 | shutil.copy() | ⚠️ 中 | frozen 模式失败 | 需修复 |
| scripts/benchmark/exp_utils.py | 302 | shutil.move() | ⚠️ 中 | 路径错误 | 需修复 |
| swift/llm/megatron/utils.py | 43 | shutil.move() | ⚠️ 低 | 权限错误忽略 | 需改进 |
| backend/routers/admin.py | 345-361 | urllib.request | ⚠️ 低 | 并发竞态 | 需改进 |

---

## 🔧 通用修复建议

### 1. **用 `os.replace()` 代替 `shutil.move()`**
```python
# ❌ 不好
shutil.move(src, dst)

# ✅ 好
os.replace(src, dst)
```

### 2. **对跨驱动器操作实现 fallback**
```python
try:
    os.replace(src, dst)
except OSError:
    # 跨驱动器：先复制，后删除
    shutil.copy2(src, dst)
    os.remove(src)
```

### 3. **在正确的目录创建临时文件**
```python
# ❌ 系统 /tmp，可能权限不足
fd, temp_path = tempfile.mkstemp()

# ✅ 在目标父目录创建
fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(target_path))
```

### 4. **使用内存而不是磁盘（适用于小文件）**
```python
# ❌ ZIP 文件保存到磁盘
with zipfile.ZipFile(zip_path, 'w') as zf:
    pass

# ✅ ZIP 文件在内存中
import io
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w') as zf:
    pass
```

### 5. **frozen 模式特殊处理**
```python
if getattr(sys, 'frozen', False):
    # 使用用户目录而不是 EXE 目录
    config_dir = Path.home() / '.aigi-holmes'
else:
    config_dir = Path(__file__).parent
```

### 6. **并发安全**
```python
# 使用文件锁或原子操作
import fcntl

with open(filepath, 'w') as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.write(data)
```

---

## 🎯 优先级修复清单

### 立刻修复（可能导致用户数据丢失）
- [ ] `swift/hub/utils/caching.py` - 缓存文件丢失
- [ ] `swift/llm/utils/media.py` - 模型资源无法加载
- [ ] `backend/routers/detect.py` - 批量下载功能故障

### 尽快修复（影响主要功能）
- [ ] `swift/tuners/base.py` - 模型保存失败
- [ ] `pyi_rthook_cwd.py` - frozen EXE 启动失败
- [ ] `scripts/benchmark/exp_utils.py` - 实验管理故障

### 按计划修复（代码质量）
- [ ] `swift/hub/file_download.py` - 完善错误处理
- [ ] `swift/llm/megatron/utils.py` - 日志不完整
- [ ] `backend/routers/admin.py` - 并发安全

---

## 📋 验证清单

完成修复后，请验证：

- [ ] 在 Windows 上测试跨驱动器文件移动
- [ ] 启用杀毒软件测试文件操作
- [ ] 使用权限受限的用户账户测试
- [ ] 测试 frozen PyInstaller EXE
- [ ] 测试低磁盘空间场景
- [ ] 并发操作压力测试
- [ ] 网络驱动器路径测试

