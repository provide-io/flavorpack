# 
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Generated protocol buffer code."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    31,
    1,
    '',
    'modules/spa.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x11modules/spa.proto\x12\rpspf_2025.spa\"\xad\x02\n\x0fSPASystemConfig\x12\x0f\n\x07\x65nabled\x18\x01 \x01(\x08\x12\x10\n\x08pvp_slot\x18\x02 \x01(\r\x12\x16\n\x0epvp_timeout_ms\x18\x03 \x01(\r\x12\x16\n\x0epvp_max_memory\x18\x04 \x01(\x04\x12\x33\n\x10pvp_capabilities\x18\x05 \x03(\x0e\x32\x19.pspf_2025.spa.Capability\x12/\n\x08\x62oundary\x18\x06 \x01(\x0b\x32\x1d.pspf_2025.spa.BoundaryConfig\x12-\n\x07sandbox\x18\x07 \x01(\x0b\x32\x1c.pspf_2025.spa.SandboxConfig\x12\x32\n\x07targets\x18\x08 \x01(\x0b\x32!.pspf_2025.spa.PerformanceTargets\"\xd9\x01\n\x0e\x42oundaryConfig\x12\x38\n\x04type\x18\x01 \x01(\x0e\x32*.pspf_2025.spa.BoundaryConfig.BoundaryType\x12\x12\n\ntimeout_ms\x18\x02 \x01(\r\x12%\n\x03ipc\x18\x03 \x01(\x0b\x32\x18.pspf_2025.spa.IPCConfig\"R\n\x0c\x42oundaryType\x12\x18\n\x14\x42OUNDARY_SYNCHRONOUS\x10\x00\x12\x12\n\x0e\x42OUNDARY_ASYNC\x10\x01\x12\x14\n\x10\x42OUNDARY_POLLING\x10\x02\"\xf8\x01\n\tIPCConfig\x12.\n\x04type\x18\x01 \x01(\x0e\x32 .pspf_2025.spa.IPCConfig.IPCType\x12\x0c\n\x04path\x18\x02 \x01(\t\x12\x13\n\x0b\x62uffer_size\x18\x03 \x01(\r\x12\x15\n\rbidirectional\x18\x04 \x01(\x08\"\x80\x01\n\x07IPCType\x12\x15\n\x11IPC_SHARED_MEMORY\x10\x00\x12\x13\n\x0fIPC_UNIX_SOCKET\x10\x01\x12\x12\n\x0eIPC_NAMED_PIPE\x10\x02\x12\x11\n\rIPC_SEMAPHORE\x10\x03\x12\x0f\n\x0bIPC_EVENTFD\x10\x04\x12\x11\n\rIPC_MACH_PORT\x10\x05\"\x88\x03\n\rSandboxConfig\x12\x36\n\x04type\x18\x01 \x01(\x0e\x32(.pspf_2025.spa.SandboxConfig.SandboxType\x12\x18\n\x10\x61llowed_syscalls\x18\x02 \x03(\t\x12\x18\n\x10\x62locked_syscalls\x18\x03 \x03(\t\x12-\n\x06limits\x18\x04 \x01(\x0b\x32\x1d.pspf_2025.spa.ResourceLimits\x12\x31\n\x02\x66s\x18\x05 \x01(\x0b\x32%.pspf_2025.spa.FilesystemRestrictions\"\xa8\x01\n\x0bSandboxType\x12\x10\n\x0cSANDBOX_NONE\x10\x00\x12\x13\n\x0fSANDBOX_SECCOMP\x10\x01\x12\x15\n\x11SANDBOX_NAMESPACE\x10\x02\x12\x18\n\x14SANDBOX_APPCONTAINER\x10\x03\x12\x17\n\x13SANDBOX_MAC_SANDBOX\x10\x04\x12\x12\n\x0eSANDBOX_PLEDGE\x10\x05\x12\x14\n\x10SANDBOX_CAPSICUM\x10\x06\"\xa6\x01\n\x0eResourceLimits\x12\x14\n\x0cmemory_bytes\x18\x01 \x01(\x04\x12\x13\n\x0b\x63pu_percent\x18\x02 \x01(\r\x12\x14\n\x0c\x66ile_handles\x18\x03 \x01(\r\x12\x0f\n\x07threads\x18\x04 \x01(\r\x12\x11\n\tprocesses\x18\x05 \x01(\r\x12\x12\n\ndisk_bytes\x18\x06 \x01(\x04\x12\x1b\n\x13network_connections\x18\x07 \x01(\r\"\x81\x01\n\x16\x46ilesystemRestrictions\x12\x15\n\rallowed_paths\x18\x01 \x03(\t\x12\x15\n\rblocked_paths\x18\x02 \x03(\t\x12\x11\n\ttemp_only\x18\x03 \x01(\x08\x12\x11\n\tread_only\x18\x04 \x01(\x08\x12\x13\n\x0btemp_prefix\x18\x05 \x01(\t\"\x8a\x01\n\x12PerformanceTargets\x12\x1e\n\x16time_to_first_pixel_ms\x18\x01 \x01(\r\x12 \n\x18verification_duration_ms\x18\x02 \x01(\r\x12\x18\n\x10\x62oundary_wait_ms\x18\x03 \x01(\r\x12\x18\n\x10total_startup_ms\x18\x04 \x01(\r\"\xea\x01\n\x11VerificationState\x12\r\n\x05magic\x18\x01 \x01(\x07\x12\x0f\n\x07version\x18\x02 \x01(\r\x12\x35\n\x05state\x18\x03 \x01(\x0e\x32&.pspf_2025.spa.VerificationState.State\x12\x12\n\nerror_code\x18\x04 \x01(\r\x12\x15\n\rmetadata_hash\x18\x05 \x01(\x0c\x12\x11\n\ttimestamp\x18\x06 \x01(\x04\"@\n\x05State\x12\x11\n\rSTATE_PENDING\x10\x00\x12\x12\n\x0eSTATE_VERIFIED\x10\x01\x12\x10\n\x0cSTATE_FAILED\x10\x02\"\x8b\x02\n\x10HandshakeMessage\x12\x32\n\x04type\x18\x01 \x01(\x0e\x32$.pspf_2025.spa.HandshakeMessage.Type\x12\x0b\n\x03pid\x18\x02 \x01(\r\x12\r\n\x05nonce\x18\x03 \x01(\x04\x12\x0c\n\x04hash\x18\x04 \x01(\x0c\x12\r\n\x05\x65rror\x18\x05 \x01(\r\"\x89\x01\n\x04Type\x12\x0e\n\nTYPE_READY\x10\x00\x12\x0c\n\x08TYPE_ACK\x10\x01\x12\x14\n\x10TYPE_AT_BOUNDARY\x10\x02\x12\x11\n\rTYPE_VERIFIED\x10\x03\x12\x0f\n\x0bTYPE_FAILED\x10\x04\x12\x13\n\x0fTYPE_PROCEEDING\x10\x05\x12\x14\n\x10TYPE_TERMINATING\x10\x06\"\x9d\x04\n\x0f\x46\x61ilureHandling\x12=\n\x07\x61\x63tions\x18\x01 \x03(\x0b\x32,.pspf_2025.spa.FailureHandling.FailureAction\x12\x1c\n\x14graceful_degradation\x18\x02 \x01(\x08\x1a\x9a\x02\n\rFailureAction\x12\x38\n\x04mode\x18\x01 \x01(\x0e\x32*.pspf_2025.spa.FailureHandling.FailureMode\x12\x43\n\x06\x61\x63tion\x18\x02 \x01(\x0e\x32\x33.pspf_2025.spa.FailureHandling.FailureAction.Action\x12\x13\n\x0blog_details\x18\x03 \x01(\x08\x12\x19\n\x11\x63leanup_resources\x18\x04 \x01(\x08\"Z\n\x06\x41\x63tion\x12\x13\n\x0f\x41\x43TION_KILL_PVP\x10\x00\x12\x13\n\x0f\x41\x43TION_CONTINUE\x10\x01\x12\x14\n\x10\x41\x43TION_TERMINATE\x10\x02\x12\x10\n\x0c\x41\x43TION_RETRY\x10\x03\"\x8f\x01\n\x0b\x46\x61ilureMode\x12\x17\n\x13\x46\x41ILURE_PVP_TIMEOUT\x10\x00\x12\x15\n\x11\x46\x41ILURE_PVP_CRASH\x10\x01\x12\x17\n\x13\x46\x41ILURE_VERIFY_FAIL\x10\x02\x12\x1a\n\x16\x46\x41ILURE_SANDBOX_BREACH\x10\x03\x12\x1b\n\x17\x46\x41ILURE_RESOURCE_EXCEED\x10\x04\"\xd0\x02\n\x16PlatformImplementation\x12@\n\x08platform\x18\x01 \x01(\x0e\x32..pspf_2025.spa.PlatformImplementation.Platform\x12\x39\n\x07sandbox\x18\x02 \x01(\x0e\x32(.pspf_2025.spa.SandboxConfig.SandboxType\x12-\n\x03ipc\x18\x03 \x01(\x0e\x32 .pspf_2025.spa.IPCConfig.IPCType\x12\x19\n\x11required_features\x18\x04 \x03(\t\x12\x13\n\x0bmin_version\x18\x05 \x01(\t\"Z\n\x08Platform\x12\x12\n\x0ePLATFORM_LINUX\x10\x00\x12\x12\n\x0ePLATFORM_MACOS\x10\x01\x12\x14\n\x10PLATFORM_WINDOWS\x10\x02\x12\x10\n\x0cPLATFORM_BSD\x10\x03*\xfd\x01\n\nCapability\x12\x13\n\x0f\x43\x41PABILITY_NONE\x10\x00\x12\x18\n\x14\x43\x41PABILITY_UI_RENDER\x10\x01\x12\x19\n\x15\x43\x41PABILITY_TEMP_FILES\x10\x02\x12\x18\n\x14\x43\x41PABILITY_IPC_SETUP\x10\x03\x12\x19\n\x15\x43\x41PABILITY_CACHE_INIT\x10\x04\x12\x1a\n\x16\x43\x41PABILITY_CONFIG_LOAD\x10\x05\x12\x19\n\x15\x43\x41PABILITY_MEMORY_MAP\x10\x06\x12\x1b\n\x17\x43\x41PABILITY_THREAD_SPAWN\x10\x07\x12\x1c\n\x18\x43\x41PABILITY_SIGNAL_HANDLE\x10\x08\x42[\n\x1eio.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'modules.spa_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\n\036io.provide.flavorpack.pspf2025Z9github.com/provide-io/flavorpack/psp/format_2025;pspf2025'
  _globals['_CAPABILITY']._serialized_start=3039
  _globals['_CAPABILITY']._serialized_end=3292
  _globals['_SPASYSTEMCONFIG']._serialized_start=37
  _globals['_SPASYSTEMCONFIG']._serialized_end=338
  _globals['_BOUNDARYCONFIG']._serialized_start=341
  _globals['_BOUNDARYCONFIG']._serialized_end=558
  _globals['_BOUNDARYCONFIG_BOUNDARYTYPE']._serialized_start=476
  _globals['_BOUNDARYCONFIG_BOUNDARYTYPE']._serialized_end=558
  _globals['_IPCCONFIG']._serialized_start=561
  _globals['_IPCCONFIG']._serialized_end=809
  _globals['_IPCCONFIG_IPCTYPE']._serialized_start=681
  _globals['_IPCCONFIG_IPCTYPE']._serialized_end=809
  _globals['_SANDBOXCONFIG']._serialized_start=812
  _globals['_SANDBOXCONFIG']._serialized_end=1204
  _globals['_SANDBOXCONFIG_SANDBOXTYPE']._serialized_start=1036
  _globals['_SANDBOXCONFIG_SANDBOXTYPE']._serialized_end=1204
  _globals['_RESOURCELIMITS']._serialized_start=1207
  _globals['_RESOURCELIMITS']._serialized_end=1373
  _globals['_FILESYSTEMRESTRICTIONS']._serialized_start=1376
  _globals['_FILESYSTEMRESTRICTIONS']._serialized_end=1505
  _globals['_PERFORMANCETARGETS']._serialized_start=1508
  _globals['_PERFORMANCETARGETS']._serialized_end=1646
  _globals['_VERIFICATIONSTATE']._serialized_start=1649
  _globals['_VERIFICATIONSTATE']._serialized_end=1883
  _globals['_VERIFICATIONSTATE_STATE']._serialized_start=1819
  _globals['_VERIFICATIONSTATE_STATE']._serialized_end=1883
  _globals['_HANDSHAKEMESSAGE']._serialized_start=1886
  _globals['_HANDSHAKEMESSAGE']._serialized_end=2153
  _globals['_HANDSHAKEMESSAGE_TYPE']._serialized_start=2016
  _globals['_HANDSHAKEMESSAGE_TYPE']._serialized_end=2153
  _globals['_FAILUREHANDLING']._serialized_start=2156
  _globals['_FAILUREHANDLING']._serialized_end=2697
  _globals['_FAILUREHANDLING_FAILUREACTION']._serialized_start=2269
  _globals['_FAILUREHANDLING_FAILUREACTION']._serialized_end=2551
  _globals['_FAILUREHANDLING_FAILUREACTION_ACTION']._serialized_start=2461
  _globals['_FAILUREHANDLING_FAILUREACTION_ACTION']._serialized_end=2551
  _globals['_FAILUREHANDLING_FAILUREMODE']._serialized_start=2554
  _globals['_FAILUREHANDLING_FAILUREMODE']._serialized_end=2697
  _globals['_PLATFORMIMPLEMENTATION']._serialized_start=2700
  _globals['_PLATFORMIMPLEMENTATION']._serialized_end=3036
  _globals['_PLATFORMIMPLEMENTATION_PLATFORM']._serialized_start=2946
  _globals['_PLATFORMIMPLEMENTATION_PLATFORM']._serialized_end=3036
# @@protoc_insertion_point(module_scope)

# 🌶️📦🔚
