"""Process-tree and pipe operations for timed Windows commands."""

import sys

if sys.platform == "win32":  # pragma: no cover
    import ctypes
    import ctypes.wintypes
    import msvcrt
    import os
    from subprocess import Popen
    from types import TracebackType
    from typing import Self

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

    class Job:
        """Track the process tree from before its first instruction."""

        creationflags = 0x00000004  # CREATE_SUSPENDED

        def __enter__(self) -> Self:
            """Create a job that does not permit child processes to
            leave.
            """
            handle: int | None = _kernel32.CreateJobObjectW(None, None)
            if handle is None:
                raise ctypes.WinError(code=ctypes.get_last_error())
            self._job_handle = handle
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            """Release the job handle."""
            del exc_type, exc_value, traceback
            _ = _kernel32.CloseHandle(self._job_handle)

        def start(self, *, process: Popen[bytes]) -> None:
            """Assign a suspended process to the job before it can
            spawn.
            """
            # PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_SUSPEND_RESUME
            access = 0x0100 | 0x0001 | 0x0800
            handle: int | None = _kernel32.OpenProcess(access, 0, process.pid)
            if handle is None:
                raise ctypes.WinError(code=ctypes.get_last_error())
            try:
                if not _kernel32.AssignProcessToJobObject(
                    self._job_handle, handle
                ):
                    raise ctypes.WinError(code=ctypes.get_last_error())
                # Popen closes the initial thread handle, so resume the
                # process through its process handle.
                status: int = _ntdll.NtResumeProcess(handle)
                if status < 0:
                    msg = (
                        "Could not resume command "
                        f"(NTSTATUS {status & 0xFFFFFFFF:#x})."
                    )
                    raise OSError(msg)
            finally:
                _ = _kernel32.CloseHandle(handle)

        def terminate(self) -> None:
            """Terminate all job members, even after the leader exits."""
            if not _kernel32.TerminateJobObject(self._job_handle, 1):
                raise ctypes.WinError(code=ctypes.get_last_error())

    def read_pipe(*, fd: int, size: int) -> bytes | None:
        """Read available pipe bytes, returning None while awaiting
        data.
        """
        available = _dword()
        # This is the only reader of the pipe. Once the peek reports bytes,
        # reading at most that many cannot wait for more output. ctypes
        # passes available by reference because argtypes declares a pointer.
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
