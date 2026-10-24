using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows.Forms;

internal static class Launcher
{
    private static string _exeDir;
    private static string _logPath;

    private static void Log(string text)
    {
        try { File.AppendAllText(_logPath, DateTime.Now.ToString("s") + " " + text + "\n"); } catch { }
    }

    private static void Extract(string resource, string dir, string tmpDir)
    {
        string zip = Path.Combine(tmpDir, resource);
        using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(resource))
        {
            if (s == null) throw new InvalidOperationException("Missing embedded " + resource);
            using (FileStream f = File.Create(zip)) { s.CopyTo(f); }
        }
        ZipFile.ExtractToDirectory(zip, dir);
        try { File.Delete(zip); } catch { }
    }

    // Each embedded app package gets an immutable extraction folder. The launcher
    // may be started again while Python still has a vendor DLL loaded; never delete
    // or overwrite the running app directory.
    private static string PrepareApp(string baseDir)
    {
        byte[] archive;
        using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("app.zip"))
        {
            if (s == null) throw new InvalidOperationException("Missing embedded app.zip");
            using (MemoryStream ms = new MemoryStream()) { s.CopyTo(ms); archive = ms.ToArray(); }
        }

        string digest;
        using (SHA256 sha = SHA256.Create())
        {
            digest = BitConverter.ToString(sha.ComputeHash(archive)).Replace("-", "").ToLowerInvariant();
        }

        string appDir = Path.Combine(baseDir, "app_" + digest.Substring(0, 16));
        string marker = Path.Combine(appDir, ".app-ok");
        try
        {
            if (File.Exists(marker) && File.ReadAllText(marker) == digest)
            {
                Log("app cache hit " + digest);
                return appDir;
            }
        }
        catch { }

        // A partial extraction may be in use after an interrupted start. Give this
        // attempt its own directory instead of deleting files that could be locked.
        if (Directory.Exists(appDir)) appDir += "_" + Guid.NewGuid().ToString("N").Substring(0, 8);
        Directory.CreateDirectory(appDir);
        string zip = Path.Combine(baseDir, "app_" + digest.Substring(0, 16) + "_" + Guid.NewGuid().ToString("N") + ".zip");
        try
        {
            File.WriteAllBytes(zip, archive);
            ZipFile.ExtractToDirectory(zip, appDir);
            File.WriteAllText(Path.Combine(appDir, ".app-ok"), digest);
            Log("app extracted " + digest + " to " + appDir);
        }
        finally
        {
            try { File.Delete(zip); } catch { }
        }
        return appDir;
    }

    [STAThread]
    private static void Main()
    {
        _exeDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        _logPath = Path.Combine(_exeDir, "launcher.log");
        try
        {
            Log("start");
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string baseDir = Path.Combine(local, "YAOModForge");
            try
            {
                Directory.CreateDirectory(baseDir);
                string probe = Path.Combine(baseDir, ".write_test");
                File.WriteAllText(probe, "1");
                File.Delete(probe);
            }
            catch
            {
                baseDir = Path.Combine(_exeDir, "YAOForgeData");
                Directory.CreateDirectory(baseDir);
            }
            Log("base " + baseDir);

            string runtimeDir = Path.Combine(baseDir, "python");
            if (!File.Exists(Path.Combine(runtimeDir, ".runtime-ok")))
            {
                if (Directory.Exists(runtimeDir)) Directory.Delete(runtimeDir, true);
                Directory.CreateDirectory(runtimeDir);
                Extract("runtime.zip", runtimeDir, baseDir);
                File.WriteAllText(Path.Combine(runtimeDir, ".runtime-ok"), "1");
                Log("runtime ready");
            }

            string appDir = PrepareApp(baseDir);
            string py = Path.Combine(runtimeDir, "python.exe");
            ProcessStartInfo psi = new ProcessStartInfo(py, "\"" + Path.Combine(appDir, "yao_forge.py") + "\"");
            psi.WorkingDirectory = appDir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.EnvironmentVariables["YAO_FORGE_DATA"] = baseDir;
            psi.EnvironmentVariables["YAO_FORGE_EXE"] = Assembly.GetExecutingAssembly().Location;
            using (Process child = new Process())
            {
                child.StartInfo = psi;
                child.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e)
                {
                    if (!String.IsNullOrEmpty(e.Data)) Log("python: " + e.Data);
                };
                child.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e)
                {
                    if (!String.IsNullOrEmpty(e.Data)) Log("python error: " + e.Data);
                };
                child.Start();
                child.BeginOutputReadLine();
                child.BeginErrorReadLine();
                Log("started app pid " + child.Id + " from " + appDir);
                child.WaitForExit();
                Log("app exited with code " + child.ExitCode);
            }
        }
        catch (Exception ex)
        {
            Log(ex.ToString());
            MessageBox.Show("ModDiver Laboratory could not start:\n\n" + ex.Message, "ModDiver Laboratory",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
