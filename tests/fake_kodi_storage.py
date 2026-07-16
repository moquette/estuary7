"""A tvOS-accurate fake of Kodi's storage layer.

WHY THIS EXISTS
---------------
On 2026-07-14 an EZ Maintenance++ restore silently destroyed the owner's customized
Apple TV main menu. Thirty-three unit tests were green the whole time, because the
fake they ran against modelled tvOS as *a dict*. A dict cannot represent the one state
that broke the box: "the NSUserDefaults key exists but the disk file is gone." The
tests agreed with a wrong mental model, so they certified the bug.

This fake has TWO layers - a key store AND a real POSIX tree - so that state is
representable, and therefore testable.

GROUND TRUTH
------------
Every rule below is transcribed from Kodi Omega source at xbmc/xbmc@f8815ee4
(TVOSFile.cpp, TVOSDirectory.cpp, TVOSNSUserDefaults.mm, FileFactory.cpp), not from
our own docs - six of which asserted a model that turned out to be false. If this fake
and Kodi ever disagree, THE FAKE IS THE BUG. Re-derive it from source, never from
intuition and never from a doc.

THE DISPATCH (FileFactory.cpp:113-121)
--------------------------------------
    if (url.IsProtocol("file") || url.GetProtocol().empty()) {
        if (CTVOSFile::WantsFile(url))  return new CTVOSFile();
        return new CPosixFile();
    }

So WantsFile is the ONLY gate. A path it rejects is plain POSIX and behaves normally.
Everything surprising about tvOS applies to, and only to, the paths it accepts.

THE RULES
---------
WantsFile(url)                                          TVOSFile.cpp:39-45
    extension is "xml" (case-insensitive, last dot)
    AND basename does NOT start with "customcontroller.SiriRemote" (case-insens)
    AND IsKeyFromPath(url)  ->  translatePathIntoKey succeeds
                            ->  the real path contains "<home>/userdata"

Read / Exists                                           TVOSFile.cpp:70-85, 113-122
    KEY FIRST, POSIX only as a fallback. A key SHADOWS the disk file.
    Kodi NEVER re-materializes the disk file from the key: MigrateUserdataXMLToNSUserDefaults
    (PreflightHandler.mm:81-93) returns early forever once UserdataMigrated is set.
    => Dropping the POSIX copy of a vectored file has ZERO fallback. This is the single
       most expensive false belief in this project's history; it is why the menu died.

Write                                                   TVOSFile.cpp:87-99, 199-212
    SetKeyData REPLACES the whole key. There is no append and no seek.
    => NEVER chunk a write to a vectored path: the last chunk is the whole file.
    The disk file is NOT touched.

Delete                                                  TVOSFile.cpp:101-111
    bool ret = DeleteKeyFromPath(url, true);
    if (!ret) { CPosixFile posix; ret = posix.Delete(url); }   // <- the "fallback"

    ...but follow it through:
      DeleteKeyFromPath  -> translatePathIntoKey() succeeds for ANY path under userdata
                         -> DeleteKey(key, true)                 TVOSNSUserDefaults.mm:271-278
      DeleteKey          -> [defaults removeObjectForKey:...]    (SILENT no-op if absent)
                         -> return [defaults synchronize] == YES (true)
                                                                 TVOSNSUserDefaults.mm:188-202
    ret is TRUE whether or not a key existed, so `if (!ret)` is UNREACHABLE for exactly
    the files CTVOSFile is dispatched for.

    => xbmcvfs.delete() on a userdata *.xml CANNOT delete the POSIX file on tvOS.
       It drops the key and reports success. Code that "deletes" such a file and trusts
       the True is leaving the disk copy behind, forever, silently.
       (Our own docs got this rule wrong in BOTH directions before it was read from source.)

listdir                                                 TVOSDirectory.cpp:48-106
    POSIX entries + key entries, merged, with NO dedupe. A file living in both layers is
    listed TWICE - which is why File Manager showed everything double after a restore.

WHAT THIS FAKE DELIBERATELY DOES NOT MODEL (do not mistake green for safe)
-------------------------------------------------------------------------
  - the ControlImage / texture-loader path (a write must go THROUGH xbmcvfs or Apple TV's
    texture loader reads it empty)  -- the OPPOSITE fix to the shadow bug above
  - the VFS-cannot-read-a-foreign-local-file bug (Stat() reports the right size while
    readBytes() returns empty, for a local file written by plain open())
  - the 512KB warn / 1MB app-termination NSUserDefaults budget
  - multiple profiles

Those are real, documented, and have each cost us a release. They are simply out of
scope HERE; a passing test against this fake says nothing about them.
"""

import os

__all__ = ["FakeKodiStorage", "make_modules"]

_SIRI = "customcontroller.siriremote"


class FakeKodiStorage:
    """Two layers: a real POSIX tree at `home`, and an NSUserDefaults key store."""

    def __init__(self, home, platform="tvos"):
        self.home = str(home)
        self.platform = platform  # "tvos" | "android"
        self.keys = {}  # key -> bytes  (NSUserDefaults)
        self.log = []

    # -- path handling ----------------------------------------------------------------

    def translate(self, path):
        """special:// -> real path. Single-profile box: profile == masterprofile."""
        p = str(path)
        for pfx in (
            "special://profile/",
            "special://masterprofile/",
            "special://userdata/",
        ):
            if p.startswith(pfx):
                return os.path.join(self.home, "userdata", p[len(pfx) :])
        if p.startswith("special://skin/"):
            return os.path.join(
                self.home, "addons", "skin.estuary7", p[len("special://skin/") :]
            )
        if p.startswith("special://temp/"):
            return os.path.join(self.home, "temp", p[len("special://temp/") :])
        if p.startswith("special://home/"):
            return os.path.join(self.home, p[len("special://home/") :])
        return p

    def _key(self, real):
        """translatePathIntoKey (TVOSNSUserDefaults.mm:27-59): under <home>/userdata."""
        userdata = os.path.join(self.home, "userdata")
        if userdata not in real:
            return None
        i = real.find("/userdata")
        return real[i:] if i != -1 else None

    def wants_file(self, path):
        """CTVOSFile::WantsFile (TVOSFile.cpp:39-45). The ONLY gate (FileFactory.cpp:117)."""
        if self.platform != "tvos":
            return False
        real = self.translate(path)
        base = os.path.basename(real)
        if base.lower().rsplit(".", 1)[-1] != "xml" or "." not in base:
            return False
        if base.lower().startswith(_SIRI):
            return False
        return self._key(real) is not None

    # -- the VFS surface --------------------------------------------------------------

    def exists(self, path):
        """Key FIRST, POSIX fallback. TVOSFile.cpp:113-122."""
        real = self.translate(path)
        if self.wants_file(path) and self._key(real) in self.keys:
            return True
        return os.path.exists(real)

    def read_bytes(self, path):
        """Key FIRST, POSIX fallback. TVOSFile.cpp:70-85."""
        real = self.translate(path)
        if self.wants_file(path):
            k = self._key(real)
            if k in self.keys:
                return bytearray(self.keys[k])
        if os.path.isfile(real):
            with open(real, "rb") as f:
                return bytearray(f.read())
        return bytearray()

    def write_bytes(self, path, data):
        """Vectored: WHOLE-key replace, disk untouched. Else: plain POSIX. TVOSFile.cpp:87-99."""
        real = self.translate(path)
        if self.wants_file(path):
            self.keys[self._key(real)] = bytes(data)  # REPLACE. Never append.
            return len(data)
        d = os.path.dirname(real)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(real, "wb") as f:
            f.write(bytes(data))
        return len(data)

    def delete(self, path):
        """Drops the KEY and returns True. NEVER touches the POSIX file. TVOSFile.cpp:101-111.

        See the module docstring: the POSIX fallback is unreachable for dispatched files
        because DeleteKey returns [defaults synchronize]==YES regardless of whether a key
        existed. Modelling the fallback as *reachable* would be modelling our old, wrong
        belief - exactly the failure this fake exists to prevent.
        """
        real = self.translate(path)
        if self.wants_file(path):
            self.keys.pop(self._key(real), None)
            return True
        if os.path.isfile(real):
            os.remove(real)
            return True
        return False

    def listdir(self, path):
        """POSIX entries + key entries, NO dedupe. TVOSDirectory.cpp:48-106."""
        real = self.translate(path)
        dirs, files = [], []
        if os.path.isdir(real):
            for name in sorted(os.listdir(real)):
                (dirs if os.path.isdir(os.path.join(real, name)) else files).append(
                    name
                )
        if self.platform == "tvos":
            prefix = self._key(os.path.join(real, ""))
            if prefix:
                for k in sorted(self.keys):
                    if k.startswith(prefix) and "/" not in k[len(prefix) :]:
                        files.append(os.path.basename(k))  # deliberately NOT deduped
        return dirs, files

    # -- test-side helpers ------------------------------------------------------------

    def orphan(self, path):
        """Reproduce the bug: vector the file into a key, then delete the POSIX copy.

        This is exactly what nsud.rewrite_userdata_xml did to
        addon_data/script.skinshortcuts/*.DATA.xml before 2026.07.14.0.
        """
        real = self.translate(path)
        with open(real, "rb") as f:
            data = f.read()
        self.keys[self._key(real)] = data
        os.remove(real)


# -- fake xbmc modules ------------------------------------------------------------------


def make_modules(store):
    """Return (xbmc, xbmcvfs, xbmcaddon) module stand-ins bound to `store`."""

    class _File:
        def __init__(self, path, mode="r"):
            self._path, self._mode, self._buf = path, mode, bytearray()

        def readBytes(self):
            return store.read_bytes(self._path)

        def write(self, data):
            self._buf += bytearray(data)
            return True

        def close(self):
            if "w" in self._mode:
                store.write_bytes(self._path, self._buf)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.close()

    class _Vfs:
        File = staticmethod(_File)
        exists = staticmethod(store.exists)
        delete = staticmethod(store.delete)
        listdir = staticmethod(store.listdir)
        translatePath = staticmethod(store.translate)

        @staticmethod
        def mkdirs(p):
            real = store.translate(p)
            if not os.path.isdir(real):
                os.makedirs(real)
            return True

    class _Xbmc:
        LOGINFO, LOGWARNING, LOGERROR, LOGDEBUG = 1, 2, 3, 0

        @staticmethod
        def log(msg, level=1):
            store.log.append(msg)

        @staticmethod
        def getSkinDir():
            return "skin.estuary7"

        @staticmethod
        def executebuiltin(cmd):
            store.log.append("builtin: %s" % cmd)

        @staticmethod
        def getCondVisibility(cond):
            # Platform conditionals only - enough for the seed's tvOS gate.
            if cond == "System.Platform.TVOS":
                return store.platform == "tvos"
            if cond == "System.Platform.Android":
                return store.platform == "android"
            return False

        @staticmethod
        def getInfoLabel(label):
            # Not a storage concern (out of this fake's real scope per the
            # module docstring) - just enough for callers that read
            # System.BuildVersion / System.ProfileName. Kodi 21 "Omega", the
            # fleet's pinned version (see CLAUDE.md).
            return {
                "System.BuildVersion": "21.3.0",
                "System.ProfileName": "Master user",
            }.get(label, "")

    class _Addon:
        _settings = {}

        def __init__(self, addon_id="skin.estuary7"):
            self._id = addon_id

        def getAddonInfo(self, key):
            return {"version": "1.0.38", "id": self._id, "name": self._id}.get(key, "")

        def getSetting(self, key):
            return _Addon._settings.get((self._id, key), "")

        def setSetting(self, key, value):
            _Addon._settings[(self._id, key)] = value

    class _XbmcAddon:
        Addon = _Addon

    return _Xbmc, _Vfs, _XbmcAddon
