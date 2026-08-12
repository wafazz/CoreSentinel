# CoreSentinel PowerShell CLI Executable Wrapper
param (
    [parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyEngine = Join-Path $ScriptDir "coresentinel.py"
python $PyEngine $Args
