using System.Collections.Concurrent;
using System.Text.Json;
using WeChatAuto.Components;
using WeChatAuto.Services;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://0.0.0.0:60443");
var app = builder.Build();

// ── 消息缓冲区 ──
var msgQueue = new ConcurrentQueue<object>();

// ── 初始化 WeChatAuto ──
var client = new WeChatClient();

lock (typeof(Program))
{
    // 给所有好友注册监听
    foreach (var f in client.GetFriends())
    {
        var name = f.Remark?.Length > 0 ? f.Remark : f.NickName;
        if (string.IsNullOrEmpty(name)) continue;
        client.AddMessageListener(name, ctx =>
        {
            foreach (var m in ctx.NewMessages)
            {
                msgQueue.Enqueue(new
                {
                    sender = m.Who ?? "",
                    content = m.MessageContent ?? "",
                    roomId = "",
                    roomName = "",
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
                });
            }
        });
    }

    // 给所有群注册监听
    foreach (var g in client.GetGroups())
    {
        if (string.IsNullOrEmpty(g.Name)) continue;
        client.AddMessageListener(g.Name, ctx =>
        {
            foreach (var m in ctx.NewMessages)
            {
                msgQueue.Enqueue(new
                {
                    sender = m.Who ?? "",
                    content = m.MessageContent ?? "",
                    roomId = g.Name,
                    roomName = g.Name,
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
                });
            }
        });
    }
}

Console.WriteLine("WeChatAuto 桥接已启动 — http://0.0.0.0:60443");
Console.WriteLine($"已监听 {client.GetFriends().Count()} 好友 + {client.GetGroups().Count()} 群");

// ── REST API ──

// 拉取消息
app.MapGet("/messages", () =>
{
    var list = new List<object>();
    while (msgQueue.TryDequeue(out var m))
        list.Add(m);
    return Results.Ok(list);
});

// 发送文本: POST /send  { "to": "...", "text": "..." }
app.MapPost("/send", (JsonElement body) =>
{
    var to = body.GetProperty("to").GetString() ?? "";
    var text = body.GetProperty("text").GetString() ?? "";
    try
    {
        client.SendWho(to, text);
        return Results.Ok(new { ok = true });
    }
    catch (Exception ex)
    {
        return Results.Problem(ex.Message, statusCode: 500);
    }
});

// 发送图片: POST /send_image  multipart: to + file
app.MapPost("/send_image", async (HttpRequest req) =>
{
    var form = await req.ReadFormAsync();
    var to = form["to"].FirstOrDefault() ?? "";
    var file = form.Files.GetFile("file");
    if (file is null || string.IsNullOrEmpty(to))
        return Results.BadRequest("missing to or file");

    var tmp = Path.GetTempFileName() + ".png";
    try
    {
        await using (var fs = File.Create(tmp))
            await file.CopyToAsync(fs);

        client.SendFile(new[] { tmp });
        return Results.Ok(new { ok = true });
    }
    catch (Exception ex)
    {
        return Results.Problem(ex.Message, statusCode: 500);
    }
    finally
    {
        try { File.Delete(tmp); } catch { }
    }
});

app.Run();
