"""Process-tree and pipe operations for timed Windows commands."""

import sys

# This guard surrounds the platform bindings and their consumers.
if sys.platform == "win32":  # pragma: no cover  # pylint: disable=too-complex
    import ctypes
    import ctypes.wintypes
    import msvcrt  # pylint: disable=import-error,useless-suppression
    import os
    from collections.abc import Generator
    from contextlib import contextmanager

    _kernel32 = ctypes.WinDLL(name="kernel32", use_last_error=True)
    _ntdll = ctypes.WinDLL(name="ntdll")
    _handle = ctypes.wintypes.HANDLE
    _dword = ctypes.wintypes.DWORD
    _bool = ctypes.wintypes.BOOL

    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    _kernel32.CreateJobObjectW.restype = _handle
    _kernel32.OpenProcess.argtypes = [_dword, _bool, _dword]
    _kernel32.OpenProcess.restype = _handle
    _kernel32.AssignProcessToJobObject.argtypes = [_handle, _handle]
    _kernel32.AssignProcessToJobObject.restype = _bool
    _kernel32.TerminateJobObject.argtypes = [_handle, ctypes.c_uint]
    _kernel32.TerminateJobObject.restype = _bool
    _kernel32.CloseHandle.argtypes = [_handle]
    _kernel32.CloseHandle.restype = _bool
    _kernel32.PeekNamedPipe.argtypes = [
        _handle,
        ctypes.c_void_p,
        _dword,
        ctypes.c_void_p,
        ctypes.POINTER(_dword),
        ctypes.c_void_p,
    ]
    _kernel32.PeekNamedPipe.restype = _bool
    _ntdll.NtResumeProcess.argtypes = [_handle]
    _ntdll.NtResumeProcess.restype = ctypes.c_long

    _ERROR_BROKEN_PIPE = 109

    CREATE_SUSPENDED = 0x00000004

    @contextmanager
    def job_object() -> Generator[int]:
        """Keep the job handle open even if the direct child exits."""
        job: int | None = _kernel32.CreateJobObjectW(None, None)
        if job is None:
            raise ctypes.WinError(code=ctypes.get_last_error())
        try:
            yield job
        finally:
            _ = _kernel32.CloseHandle(job)

    def start_in_job(*, job: int, pid: int) -> None:
        """Assign a suspended command to the job before it can spawn."""
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_SUSPEND_RESUME
        handle: int | None = _kernel32.OpenProcess(0x0901, 0, pid)
        if handle is None:
            raise ctypes.WinError(code=ctypes.get_last_error())
        try:
            if not _kernel32.AssignProcessToJobObject(job, handle):
                raise ctypes.WinError(code=ctypes.get_last_error())
            # `Popen` closes the initial thread handle.
            status: int = _ntdll.NtResumeProcess(handle)
            if status < 0:
                msg = f"Could not resume command (NTSTATUS {status:#x})."
                raise OSError(msg)
        finally:
            _ = _kernel32.CloseHandle(handle)

    def terminate_job(*, job: int) -> None:
        """Terminate all job members, even after the leader exits."""
        if not _kernel32.TerminateJobObject(job, 1):
            raise ctypes.WinError(code=ctypes.get_last_error())

    def read_pipe(*, fd: int, size: int) -> bytes | None:
        """Read available pipe bytes, returning None while awaiting
        data.
        """
        available = _dword(value=0)
        # This is the only reader of the pipe. Once the peek reports bytes,
        # reading at most that many cannot wait for more output. The native
        # signature declares a pointer, so available is passed by reference.
        if not _kernel32.PeekNamedPipe(
            msvcrt.get_osfhandle(fd),
            None,
            0,
            None,
            available,
            None,
        ):
            error = ctypes.get_last_error()
            if error == _ERROR_BROKEN_PIPE:
                return b""
            raise ctypes.WinError(code=error)
        if available.value == 0:
            return None
        return os.read(fd, min(size, available.value))
