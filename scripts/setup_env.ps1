<#
.SYNOPSIS
    report-prep 环境修复（Windows）。

.DESCRIPTION
    修三件事：
      1) 收紧 %LOCALAPPDATA%\swc 权限（去掉 Everyone / Authenticated Users 的宽松 ACE）
      2) 可选：建最小权限缓存目录，并用 subst 虚拟盘绕开父目录 ACE 检查
      3) 测试 slidep 是否恢复，可选把 SWC_NATIVE_BINDING_CACHE 持久化到用户环境变量

.PARAMETER UseVirtualDrive
    创建虚拟盘（默认 X:）指向最小权限目录，彻底绕开 C:\ 根目录的宽松 ACE。

.PARAMETER DriveLetter
    虚拟盘符，默认 X。

.PARAMETER Persist
    把 SWC_NATIVE_BINDING_CACHE 写入用户环境变量（setx），新开终端生效。

.PARAMETER DryRun
    只打印将要执行的操作，不改任何东西。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -DryRun

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -UseVirtualDrive -Persist
#>
[CmdletBinding()]
param(
    [switch]$UseVirtualDrive,
    [string]$DriveLetter = "X",
    [switch]$Persist,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

function Write-Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Note($msg) { Write-Host "  --  $msg" -ForegroundColor Gray }
function Write-Bad($msg)  { Write-Host "  XX  $msg" -ForegroundColor Red }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "report-prep 环境修复（Windows）"
Write-Host ("用户：{0}\{1}    管理员：{2}" -f $env:USERDOMAIN, $env:USERNAME, $isAdmin)
if ($DryRun) { Write-Note "DryRun：只打印操作，不改动系统" }

# ---------- 1. 收紧 SWC 缓存目录 ----------
Write-Step "检查 SWC 缓存目录权限"
$swc = Join-Path $env:LOCALAPPDATA "swc"
if (Test-Path $swc) {
    $acl = Get-Acl $swc
    $risky = @($acl.Access | Where-Object { $_.IdentityReference -match "Everyone|Authenticated Users|S-1-1-0|S-1-5-11" })
    if ($risky.Count -gt 0) {
        Write-Note ("发现 {0} 条宽松 ACE，开始收紧" -f $risky.Count)
        if (-not $DryRun) {
            icacls $swc /inheritance:d 2>&1 | Out-Null
            icacls $swc /remove:g "*S-1-1-0" 2>&1 | Out-Null
            icacls $swc /remove:g "*S-1-5-11" 2>&1 | Out-Null
            icacls $swc /grant:r "$($env:USERNAME):(OI)(CI)F" 2>&1 | Out-Null
        }
        Write-Ok "已移除 Everyone / Authenticated Users，保留当前用户完全控制"
    } else {
        Write-Ok "权限已正常，无需修改"
    }
} else {
    Write-Note "$swc 尚不存在，首次运行 slidep 时自动创建"
}

# ---------- 2. 可选：虚拟盘 ----------
$cacheValue = $null
if ($UseVirtualDrive) {
    $letter = $DriveLetter.TrimEnd(":")
    $hostDir = "C:\swcroot"
    if (Test-Path "D:\") { $hostDir = "D:\swcroot" }
    $cache = Join-Path $hostDir "cache"
    $cacheValue = "${letter}:/cache"

    Write-Step ("准备虚拟盘 {0}: -> {1}" -f $letter, $hostDir)
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $cache | Out-Null
        icacls $hostDir /inheritance:r 2>&1 | Out-Null
        icacls $hostDir /grant:r "$($env:USERNAME):(OI)(CI)F" "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" 2>&1 | Out-Null
        $existing = @(subst | Where-Object { $_ -match ("^" + $letter + ":") })
        if ($existing.Count -gt 0) {
            Write-Note ("{0}: 已被占用：{1}" -f $letter, $existing[0])
        } else {
            cmd /c "subst ${letter}: $hostDir" 2>&1 | Out-Null
        }
        if (Test-Path "${letter}:\") {
            Write-Ok ("虚拟盘可用，缓存目录 {0}" -f $cache)
        } else {
            Write-Bad "虚拟盘创建失败，换一个盘符试：-DriveLetter Y"
        }
    } else {
        Write-Note ("将创建 {0} 并 subst {1}: {2}" -f $cache, $letter, $hostDir)
    }
    $env:SWC_NATIVE_BINDING_CACHE = $cacheValue
    Write-Ok ("本次会话已设置 SWC_NATIVE_BINDING_CACHE={0}" -f $cacheValue)
}

# ---------- 3. 测试 slidep ----------
Write-Step "测试 slidep"
$slidepCmd = Get-Command slidep -ErrorAction SilentlyContinue
if (-not $slidepCmd) {
    Write-Note "未找到 slidep：PPT 阶段可改用 python-pptx，或安装 WorkBuddy workbuddy-pptx 技能"
} else {
    $out = (& slidep --version 2>&1 | Out-String)
    if ($out -match "native binding" -or $out -match "Failed to load") {
        Write-Bad "仍报原生模块加载失败"
        if (-not $UseVirtualDrive) {
            Write-Note "加参数重试：-UseVirtualDrive -Persist"
        } else {
            Write-Note "检查磁盘是否为 NTFS；或在 references/environment.md 查「父目录 ACE」一节"
        }
    } else {
        $first = ($out.Trim() -split "`n")[0]
        Write-Ok ("slidep 可用：{0}" -f $first.Trim())
    }
}

# ---------- 4. 持久化 ----------
if ($Persist) {
    Write-Step "写入用户环境变量"
    if (-not $cacheValue) {
        $cacheValue = $env:SWC_NATIVE_BINDING_CACHE
    }
    if (-not $cacheValue) { $cacheValue = "X:/cache" }
    if (-not $DryRun) {
        setx SWC_NATIVE_BINDING_CACHE $cacheValue 2>&1 | Out-Null
    }
    Write-Ok ("SWC_NATIVE_BINDING_CACHE={0}（新开终端生效）" -f $cacheValue)
}

Write-Host ""
Write-Host "完成。提醒两点：" -ForegroundColor Cyan
Write-Host "  1) subst 虚拟盘重启后失效；重启后重跑本脚本，或把 subst 命令放进任务计划。"
Write-Host "  2) 每个新终端都要有 SWC_NATIVE_BINDING_CACHE；用了 -Persist 就不用再设。"
Write-Host "  3) 回到 Skill 目录跑：python scripts/doctor.py --fix-hint"
