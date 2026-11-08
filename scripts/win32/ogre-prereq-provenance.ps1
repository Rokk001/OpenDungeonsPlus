# Hash the exact dependency inputs and installed binaries used by the Windows build.
# Only install-ogre-prereq.ps1 writes the receipt, after both INSTALL targets succeed.
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop

function Get-OgrePrereqPatchHashes {
    # Return the complete patch set required by the pinned Ogre source revision.
    $taskHashes = [ordered]@{}
    foreach ($taskName in @('ogre14-multiwindow-settings.patch', 'ogre14-short-emitter.patch',
        'ogre14-light-position-cache.patch', 'ogre14-discard-lock-unsynchronized.patch',
        'ogre14-gl3plus-program-shutdown.patch')) {
        $taskHashes[$taskName] = (Get-FileHash -LiteralPath (Join-Path "$PSScriptRoot\patches" $taskName) -Algorithm SHA256).Hash
    }
    return $taskHashes
}

function Get-OgrePrereqBinaryHashes {
    # Include every Ogre DLL copied to the game runtime and both installed configurations.
    param([Parameter(Mandatory = $true)][string]$DependencyRoot)
    $taskHashes = [ordered]@{}
    foreach ($taskSuffix in @('', '_d')) {
        foreach ($taskName in @('OgreBites', 'OgreRTShaderSystem', 'OgreOverlay', 'OgreMain',
            'Plugin_ParticleFX', 'Plugin_OctreeSceneManager', 'Codec_STBI', 'RenderSystem_GL3Plus')) {
            $taskFile = "$taskName$taskSuffix.dll"
            $taskHashes[$taskFile] = (Get-FileHash -LiteralPath (Join-Path "$DependencyRoot\install\bin" $taskFile) -Algorithm SHA256).Hash
        }
    }
    return $taskHashes
}

function Assert-OgrePrereqProvenance {
    # Refuse an old, partially replaced or differently patched dependency installation.
    param([Parameter(Mandatory = $true)][string]$DependencyRoot)
    $taskReceiptPath = Join-Path $DependencyRoot 'install\share\opendungeons-plus\ogre-prereq.json'
    if (-not (Test-Path -LiteralPath $taskReceiptPath -PathType Leaf)) {
        throw 'Patched OGRE install receipt is missing. Run install-ogre-prereq.ps1 in the permitted dependency build flow before configuring or preparing the runtime.'
    }
    $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
    if ($taskReceipt.schema -ne 1 -or $taskReceipt.commit -ne 'f906880885f6014ca9b5bd8aaa09b399394d5676') {
        throw 'Patched OGRE install receipt has an unsupported schema or source revision.'
    }
    foreach ($taskPair in @(
        @{ Expected = (Get-OgrePrereqPatchHashes); Recorded = $taskReceipt.patches },
        @{ Expected = (Get-OgrePrereqBinaryHashes -DependencyRoot $DependencyRoot); Recorded = $taskReceipt.binaries }
    )) {
        if ($null -eq $taskPair.Recorded -or @($taskPair.Recorded.PSObject.Properties).Count -ne $taskPair.Expected.Count) {
            throw 'Patched OGRE install receipt is incomplete.'
        }
        foreach ($taskName in $taskPair.Expected.Keys) {
            $taskProperty = $taskPair.Recorded.PSObject.Properties[$taskName]
            if ($null -eq $taskProperty -or $taskProperty.Value -ne $taskPair.Expected[$taskName]) {
                throw "Patched OGRE input or installed DLL has changed: $taskName. Rebuild through install-ogre-prereq.ps1."
            }
        }
    }
    Write-Output 'Patched OGRE install receipt and runtime DLL hashes verified.'
}
