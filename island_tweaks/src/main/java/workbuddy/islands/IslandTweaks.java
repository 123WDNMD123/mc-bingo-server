package workbuddy.islands;

import net.milkbowl.vault.economy.Economy;
import org.bukkit.*;
import org.bukkit.block.Biome;
import org.bukkit.block.Block;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.*;
import org.bukkit.event.*;
import org.bukkit.event.entity.CreatureSpawnEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.EntityPortalEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerPortalEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.SkullMeta;
import org.bukkit.plugin.RegisteredServiceProvider;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;
import world.bentobox.bentobox.BentoBox;
import world.bentobox.bentobox.api.events.BentoBoxReadyEvent;
import world.bentobox.bentobox.api.events.island.IslandEvent;
import world.bentobox.bentobox.api.user.User;
import world.bentobox.bentobox.database.Database;
import world.bentobox.bentobox.database.objects.Island;
import world.bentobox.bentobox.managers.island.NewIsland;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public final class IslandTweaks extends JavaPlugin implements Listener {
    private Economy economy;
    private BentoBox bento;
    private YamlConfiguration data;
    private File dataFile;
    private int stage;
    /**
     * 缓存的世界引用。禁止直接读它——插件 enable 早于 bskyblock_world 加载
     * （实测差约 9 秒），enable 时缓存必为 null。所有访问都必须走 world()。
     */
    private World worldCache;
    /** 母岛恢复重试任务；成功一次后自行取消。 */
    private BukkitTask hubRetryTask;
    private boolean hubRestored;
    /** 回家点是否通过回读校验（区别于 hubRestored：后者只表示流程跑完）。 */
    private boolean hubRestoredVerified;
    private final Map<UUID, Long> contributions = new HashMap<>();
    private final Map<UUID, Double> mobEarnings = new HashMap<>();
    private final Set<UUID> joining = ConcurrentHashMap.newKeySet();
    private final List<Stage> stages = new ArrayList<>();
    private final Map<Integer, ShopItem> shopItems = new HashMap<>();
    private final Set<String> decoratedHomes = ConcurrentHashMap.newKeySet();

    private static final class Stage {
        String name; Map<Material, Integer> needs; Map<Material, Double> rates = new EnumMap<>(Material.class); Map<Material, Integer> delivered = new EnumMap<>(Material.class);
    }
    private static final class ShopItem {
        Material material; int amount; int price; String name;
    }

    /** 母岛回家点唯一标准值（D-007）。fix_spawn.py 与 Essentials/spawn.yml 必须与之一致。 */
    private static final double HUB_HOME_X = 0.5;
    private static final double HUB_HOME_Y = 120.0;
    private static final double HUB_HOME_Z = 5.5;
    /** 私人岛回家点相对岛心的偏移（落在正南步道上），与母岛 Z 偏移保持一致。 */
    private static final double HOME_OFFSET_X = 0.5;
    private static final double HOME_Y = 120.0;
    private static final double HOME_OFFSET_Z = 5.5;

    /**
     * 惰性解析 bskyblock_world。世界尚未加载时返回 null，调用方须自行判空。
     * 解析成功后缓存，后续调用零开销。
     */
    private World world() {
        if (worldCache == null) worldCache = Bukkit.getWorld("bskyblock_world");
        return worldCache;
    }

    @Override public void onEnable() {
        bento = BentoBox.getInstance();
        RegisteredServiceProvider<Economy> rsp = getServer().getServicesManager().getRegistration(Economy.class);
        if (rsp == null) { getLogger().severe("未找到 Vault 经济服务，插件停用"); getServer().getPluginManager().disablePlugin(this); return; }
        economy = rsp.getProvider();
        dataFile = new File(getDataFolder(), "progress.yml");
        data = YamlConfiguration.loadConfiguration(dataFile);
        stage = data.getInt("stage", 0);
        loadStages(); loadShop();
        ConfigurationSection c = data.getConfigurationSection("contributions");
        if (c != null) for (String key : c.getKeys(false)) contributions.put(UUID.fromString(key), c.getLong(key));
        getServer().getPluginManager().registerEvents(this, this);
        // 注意：此处不解析 world。插件 enable 早于 bskyblock_world 加载，
        // 世界由 world() 在真正需要时惰性获取。
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            World w = world();
            if (w != null && !w.getPlayers().isEmpty()) updateHolograms();
        }, 100L, 100L);
        // 母岛恢复挂到 BentoBox 就绪事件（见 onBentoReady）；同时安排一个
        // 周期重试任务兜底，避免事件在某些加载路径下未触发导致永久跳过。
        hubRetryTask = Bukkit.getScheduler().runTaskTimer(this, () -> {
            if (hubRestored) return;
            tryRestoreHub("retry");
        }, 200L, 200L);
        getLogger().info("浮岛物语联动已启用：公共修复阶段 " + stage + "，云币经济已连接");
    }

    /** BentoBox 全部加载完成后触发：此时世界与岛屿数据库均已就绪。 */
    @EventHandler public void onBentoReady(BentoBoxReadyEvent event) {
        tryRestoreHub("BentoBoxReadyEvent");
    }

    /**
     * 恢复/校验独立公共母岛。幂等：可重复调用，成功一次后置 hubRestored 并停止重试。
     * @return true 表示本次已成功恢复
     */
    private synchronized boolean tryRestoreHub(String trigger) {
        if (hubRestored) return true;
        World w = world();
        if (w == null) {
            getLogger().info("母岛恢复等待世界加载（触发源：" + trigger + "）");
            return false;
        }
        try {
            restoreHub(w);
            hubRestored = true;
            if (hubRetryTask != null) { hubRetryTask.cancel(); hubRetryTask = null; }
            return true;
        } catch (Exception e) {
            getLogger().severe("恢复公共母岛失败（触发源：" + trigger + "）: " + e);
            return false;
        }
    }

    @Override public void onDisable() {
        if (hubRetryTask != null) { hubRetryTask.cancel(); hubRetryTask = null; }
        saveData();
    }

    private void loadStages() {
        stages.clear();
        addStage("云间仓库", needs("OAK_LOG",128,"COBBLESTONE",256,"WHEAT",64), 0.05, 0.05, 0.25);
        addStage("共生农场", needs("CARROT",64,"POTATO",64,"SUGAR_CANE",32,"DIRT",128), 0.25, 0.25, 0.25);
        addStage("远航码头", needs("STONE_BRICKS",192,"IRON_INGOT",32,"OAK_LOG",128), 0.20, 2.0, 0.10);
        addStage("引航灯塔", needs("QUARTZ",128,"GOLD_INGOT",32,"ENDER_PEARL",16), 0.50, 3.0, 3.0);
    }
    private Map<Material, Integer> needs(Object... values) {
        Map<Material, Integer> out = new LinkedHashMap<>();
        for (int i=0; i<values.length; i+=2) out.put(Material.valueOf((String)values[i]), (Integer)values[i+1]);
        return out;
    }
    private void addStage(String name, Map<Material,Integer> needs, double... rates) {
        Stage s = new Stage(); s.name=name; s.needs=needs; stages.add(s);
        int rate=0; for(Material m:needs.keySet()) s.rates.put(m,rates[Math.min(rate++,rates.length-1)]);
        int index = stages.size()-1;
        for (Material m : needs.keySet()) s.delivered.put(m, data.getInt("stages."+index+"."+m.name(),0));
    }
    private void loadShop() {
        shopItems.clear();
        addShop(10,Material.OAK_SAPLING,1,12,"橡树树苗"); addShop(11,Material.WHEAT_SEEDS,4,5,"小麦种子");
        addShop(9,Material.IRON_INGOT,1,80,"铁锭补给");
        addShop(12,Material.WATER_BUCKET,1,30,"水桶"); addShop(13,Material.LAVA_BUCKET,1,40,"岩浆桶");
        addShop(14,Material.BONE_MEAL,8,10,"骨粉"); addShop(15,Material.TORCH,16,6,"火把");
        addShop(16,Material.WHITE_BED,1,40,"白色床"); addShop(19,Material.OAK_LEAVES,16,15,"橡树叶");
        addShop(20,Material.MOSS_BLOCK,8,20,"苔藓块"); addShop(21,Material.FLOWERING_AZALEA,1,30,"盛开的杜鹃");
        addShop(22,Material.LANTERN,4,24,"灯笼"); addShop(23,Material.BOOKSHELF,2,40,"书架");
        addShop(24,Material.BLUE_ORCHID,1,20,"兰花"); addShop(25,Material.SPORE_BLOSSOM,1,80,"孢子花");
    }
    private void addShop(int slot, Material m, int amount, int price, String name) {
        ShopItem s = new ShopItem(); s.material=m; s.amount=amount; s.price=price; s.name=name; shopItems.put(slot,s);
    }
    private void saveData() {
        if (data == null) return;
        data.set("stage",stage);
        Map<String,Object> cs = new HashMap<>();
        for (Map.Entry<UUID,Long> e : contributions.entrySet()) cs.put(e.getKey().toString(),e.getValue());
        data.set("contributions",cs);
        for (int i=0;i<stages.size();i++) for (Map.Entry<Material,Integer> e : stages.get(i).delivered.entrySet()) data.set("stages."+i+"."+e.getKey().name(),e.getValue());
        try { if (!getDataFolder().exists()) getDataFolder().mkdirs(); data.save(dataFile); }
        catch (IOException e) { getLogger().severe("保存公共进度失败: "+e.getMessage()); }
    }

    @EventHandler public void onJoin(PlayerJoinEvent event) {
        Player p=event.getPlayer();
        if (!joining.add(p.getUniqueId())) return;
        scheduleIslandSetup(p, 40L, 0);
    }

    /** 建岛尝试次数上限；超过则放弃并提示手动 /is create，避免无限重试刷屏。 */
    private static final int MAX_SETUP_ATTEMPTS = 10;

    /**
     * 延迟为玩家准备私人岛。世界尚未加载时自动重试（最多 MAX_SETUP_ATTEMPTS 次），
     * 修复此前 world 恒为 null 导致新玩家永远拿不到岛的问题。
     */
    private void scheduleIslandSetup(Player p, long delay, int attempt) {
        Bukkit.getScheduler().runTaskLater(this, () -> {
            World world = world();
            if (world == null) {
                // 保留 joining 占位，避免重试期间再次进服触发并行建岛
                if (attempt + 1 < MAX_SETUP_ATTEMPTS && p.isOnline()) {
                    scheduleIslandSetup(p, 100L, attempt + 1);
                } else {
                    joining.remove(p.getUniqueId());
                    getLogger().severe("bskyblock_world 始终未加载，无法为玩家 " + p.getName() + " 建岛");
                    if (p.isOnline()) p.sendMessage("§c[浮岛] 世界尚未就绪，请稍后输入 /is create 重试。");
                }
                return;
            }
            joining.remove(p.getUniqueId());
            if (!p.isOnline()) return;
            if (!bento.getIslands().hasIsland(world,p.getUniqueId())) {
                p.sendMessage("§b[浮岛] §f正在为你准备一座新岛，请稍等……");
                try {
                    Island island=NewIsland.builder().player(User.getInstance(p)).addon(bento.getIWM().getAddon(world).orElseThrow()).reason(IslandEvent.Reason.CREATE).name("default").build();
                    decorateHome(island,p);
                    bento.getIslands().homeTeleportAsync(world,p).thenAccept(ok -> p.sendMessage(ok ? "§a[浮岛] 云上家园已就绪。小屋、农田与刷石区都归你；再去 /is spawn 看看公共工地吧。" : "§e[浮岛] 岛屿已创建，请输入 /is go 回家。"));
                } catch (Exception e) { getLogger().severe("创建私人岛失败: "+e); p.sendMessage("§c[浮岛] 建岛失败，请输入 /is create 重试。"); }
            } else {
                bento.getIslands().homeTeleportAsync(world,p);
            }
        }, delay);
    }

    @EventHandler public void onIslandCreated(IslandEvent event) {
        if(event.getReason()!=IslandEvent.Reason.CREATED && event.getReason()!=IslandEvent.Reason.RESETTED) return;
        if(event.getIsland().isSpawn()) return;
        Player p=Bukkit.getPlayer(event.getPlayerUUID());
        Bukkit.getScheduler().runTaskLater(this,()->{
            World world = world();
            if (world == null) { getLogger().severe("onIslandCreated 时世界未加载，跳过装饰"); return; }
            decorateHome(event.getIsland(),p);
            if(p!=null && p.isOnline()) { bento.getIslands().setHomeLocation(event.getIsland(),new Location(world,event.getIsland().getX()+HOME_OFFSET_X,HOME_Y,event.getIsland().getZ()+HOME_OFFSET_Z,0f,0f),""); bento.getIslands().homeTeleportAsync(world,p); }
        },20L);
    }

    @EventHandler(ignoreCancelled=true) public void onMobDeath(EntityDeathEvent event) {
        LivingEntity mob=event.getEntity(); Player killer=mob.getKiller();
        if (killer==null || mob instanceof Player || mob instanceof ArmorStand) return;
        CreatureSpawnEvent.SpawnReason reason=mob.getEntitySpawnReason();
        if (reason!=CreatureSpawnEvent.SpawnReason.NATURAL && reason!=CreatureSpawnEvent.SpawnReason.REINFORCEMENTS && reason!=CreatureSpawnEvent.SpawnReason.PATROL && reason!=CreatureSpawnEvent.SpawnReason.RAID) return;
        double base;
        switch (mob.getType()) {
            case ZOMBIE: case SKELETON: case SPIDER: case HUSK: case STRAY: base=1; break;
            case CREEPER: case ENDERMAN: case WITCH: case DROWNED: base=2; break;
            case BLAZE: case PIGLIN_BRUTE: case WITHER_SKELETON: base=3; break;
            case GHAST: case HOGLIN: case ZOGLIN: base=5; break;
            case WARDEN: base=100; break;
            case ENDER_DRAGON: base=500; break;
            case WITHER: base=200; break;
            default: return;
        }
        int level=0;
        for (String tag:mob.getScoreboardTags()) if (tag.startsWith("level")) { try { level=Integer.parseInt(tag.replaceAll("[^0-9]","")); } catch(NumberFormatException ignored){} }
        double reward=Math.min(25,base*(1+Math.min(level,50)*0.04));
        economy.depositPlayer(killer,reward);
        mobEarnings.merge(killer.getUniqueId(),reward,Double::sum);
        killer.sendActionBar(net.kyori.adventure.text.Component.text("§6+"+String.format(Locale.ROOT,"%.1f",reward)+" 云币"));
    }

    @EventHandler(ignoreCancelled=true) public void onPortal(PlayerPortalEvent event) {
        if (event.getTo().getWorld()==null) return;
        String name=event.getTo().getWorld().getName();
        if (name.endsWith("_nether") && stage<2) { event.setCancelled(true); event.getPlayer().sendMessage("§e[浮岛] 远航码头尚未修复，先去 /hub contribute 贡献力量吧。"); }
        if (name.endsWith("_the_end") && stage<3) { event.setCancelled(true); event.getPlayer().sendMessage("§e[浮岛] 引航灯塔尚未点亮，末地航线暂未开放。"); }
    }

    @Override public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (args.length > 0 && args[0].equalsIgnoreCase("refresh") && sender.hasPermission("islandtweaks.admin")) {
            applyStage(); sender.sendMessage("[浮岛] 母岛建筑已按当前进度重建"); return true;
        }
        if (!(sender instanceof Player)) { sender.sendMessage("请由玩家执行"); return true; }
        Player p=(Player)sender;
        if (command.getName().equals("cloudshop")) { openShop(p); return true; }
        if (args.length==0 || args[0].equalsIgnoreCase("progress")) { showProgress(p); return true; }
        if (args[0].equalsIgnoreCase("contribute")) { contribute(p); return true; }
        if (args[0].equalsIgnoreCase("shop")) { openShop(p); return true; }
        if (args[0].equalsIgnoreCase("refresh") && p.hasPermission("islandtweaks.admin")) { applyStage(); p.sendMessage("§a母岛建筑已按当前进度重建"); return true; }
        send(p,"§b/hub progress §7查看全服进度；§b/hub contribute §7提交当前所需物资；§b/cloudshop §7打开补给商店"); return true;
    }
    private void send(Player p,String text){ p.sendMessage("§b[浮岛] §f"+text); }
    private void showProgress(Player p) {
        if (stage>=stages.size()) { send(p,"§a母岛四期工程已全部完成。你的总贡献：§6"+contributions.getOrDefault(p.getUniqueId(),0L)+" 云币"); return; }
        Stage s=stages.get(stage); send(p,"§e第 "+(stage+1)+"/4 期 · "+s.name+" §7（你的累计贡献 "+contributions.getOrDefault(p.getUniqueId(),0L)+" 云币）");
        for (Map.Entry<Material,Integer> e:s.needs.entrySet()) p.sendMessage("  §f"+friendly(e.getKey())+" §b"+s.delivered.get(e.getKey())+"§7/§f"+e.getValue());
        p.sendMessage("§7把所需材料放在背包，输入 §b/hub contribute §7即可提交。");
    }
    private String friendly(Material m) {
        Map<Material,String> names=new EnumMap<>(Material.class);
        names.put(Material.OAK_LOG,"橡木原木");names.put(Material.COBBLESTONE,"圆石");names.put(Material.WHEAT,"小麦");
        names.put(Material.CARROT,"胡萝卜");names.put(Material.POTATO,"马铃薯");names.put(Material.SUGAR_CANE,"甘蔗");names.put(Material.DIRT,"泥土");
        names.put(Material.STONE_BRICKS,"石砖");names.put(Material.IRON_INGOT,"铁锭");names.put(Material.QUARTZ,"下界石英");
        names.put(Material.GOLD_INGOT,"金锭");names.put(Material.ENDER_PEARL,"末影珍珠"); return names.getOrDefault(m,m.name());
    }
    private void contribute(Player p) {
        if (stage>=stages.size()) { send(p,"§a母岛已全部修复，感谢你的参与。可以通过玩家商店继续流通物资。"); return; }
        World world = world();
        if (world==null || !world.equals(p.getWorld()) || Math.abs(p.getLocation().getX())>32 || Math.abs(p.getLocation().getZ())>32) { send(p,"请先到 §b/is spawn §f的母岛工地提交物资。"); return; }
        Stage s=stages.get(stage); int count=0; double reward=0;
        for (Map.Entry<Material,Integer> e:s.needs.entrySet()) {
            int remaining=e.getValue()-s.delivered.get(e.getKey());
            int have=0; for(ItemStack item:p.getInventory().getContents()) if(item!=null&&item.getType()==e.getKey()) have+=item.getAmount();
            int take=Math.min(remaining,have);
            if(take>0) { remove(p,e.getKey(),take); s.delivered.put(e.getKey(),s.delivered.get(e.getKey())+take); count+=take; reward+=take*s.rates.get(e.getKey()); }
        }
        if(count==0) { send(p,"背包里还没有当前需要的物资；输入 §b/hub progress §f查看清单。"); return; }
        economy.depositPlayer(p,reward);
        contributions.merge(p.getUniqueId(),Math.round(reward),Long::sum);
        send(p,"§a成功提交 "+count+" 份物资，获得 §6"+String.format(Locale.ROOT,"%.2f",reward)+" 云币§a。");
        p.playSound(p.getLocation(),Sound.ENTITY_PLAYER_LEVELUP,0.7f,1.4f);
        world.spawnParticle(Particle.HAPPY_VILLAGER,p.getLocation().add(0,1,0),24,0.6,0.6,0.6,0.1);
        boolean done=true; for(Material m:s.needs.keySet()) if(s.delivered.get(m)<s.needs.get(m)) done=false;
        if(done) { stage++; applyStage(); Bukkit.broadcastMessage("§b☁ §f"+p.getName()+" 完成了最后一份交付，§e"+s.name+" §f修复完成！"); }
        else { buildCurrentSite(); updateHolograms(); }
        saveData();
    }
    private void remove(Player p,Material material,int amount) {
        for(ItemStack item:p.getInventory().getContents()) {
            if(item==null||item.getType()!=material)continue;
            int n=Math.min(amount,item.getAmount()); item.setAmount(item.getAmount()-n);amount-=n;if(amount<=0)break;
        }
    }
    private void openShop(Player p) {
        Inventory inv=Bukkit.createInventory(p,36,"§b☁ 云间补给站");
        for(Map.Entry<Integer,ShopItem> e:shopItems.entrySet()) {
            ShopItem s=e.getValue(); ItemStack item=new ItemStack(s.material,s.amount); ItemMeta meta=item.getItemMeta();
            meta.setDisplayName("§f"+s.name);meta.setLore(Arrays.asList("§6"+s.price+" 云币","§7点击购买，官方商店不收购玩家物资"));item.setItemMeta(meta);inv.setItem(e.getKey(),item);
        }
        p.openInventory(inv);
    }
    @EventHandler(ignoreCancelled=true) public void onInventoryClick(org.bukkit.event.inventory.InventoryClickEvent event) {
        if(!event.getView().getTitle().equals("§b☁ 云间补给站"))return;
        event.setCancelled(true); if(!(event.getWhoClicked() instanceof Player))return;
        ShopItem s=shopItems.get(event.getRawSlot());if(s==null)return; Player p=(Player)event.getWhoClicked();
        if(!economy.has(p,s.price)){send(p,"云币不足：需要 "+s.price+"，当前余额 "+String.format(Locale.ROOT,"%.2f",economy.getBalance(p)));return;}
        if(p.getInventory().firstEmpty()==-1){send(p,"背包已满，先腾出一格吧。");return;}
        economy.withdrawPlayer(p,s.price);p.getInventory().addItem(new ItemStack(s.material,s.amount));send(p,"§a购买 "+s.name+" ×"+s.amount+"，支出 "+s.price+" 云币。");
    }

    private void applyStage() {
        if(world()==null){ getLogger().warning("applyStage 跳过：bskyblock_world 尚未加载"); return; }
        buildHub(); for(int i=0;i<Math.min(stage,4);i++) completeBuilding(i);
        if(stage<4) buildCurrentSite();
        updateHolograms();
    }
    private void updateHolograms() {
        World world = world();
        if(world==null)return;
        for(Entity e:new ArrayList<>(world.getEntities())) if(e.getScoreboardTags().contains("island-hub-text"))e.remove();
        hologram(0.5,124,0.5,"§b§l云间母岛","§f全服共建 · "+completedPercent()+"%","§e当前："+(stage<4?stages.get(stage).name:"四期工程全部完成"));
        Location[] sites={new Location(world,-13,124,-7),new Location(world,13,124,-7),new Location(world,0,124,-25),new Location(world,0,124,23)};
        for(int i=0;i<4;i++){
            Stage s=stages.get(i);String detail=i<stage?"§a已修复 · 欢迎回来":(i==stage?"§e右键工地提交材料":"§7等待前置工程");
            if(i==stage){int have=0,total=0;for(Material m:s.needs.keySet()){have+=s.delivered.get(m);total+=s.needs.get(m);}detail="§e"+have+" / "+total+" 份材料";}
            hologram(sites[i].getX(),sites[i].getY(),sites[i].getZ(),"§f§l"+(i+1)+". "+s.name,detail,i==stage?"§b/hub contribute":"");
        }
    }
    private void hologram(double x,double y,double z,String... lines) {
        World world = world();
        if (world == null) { getLogger().warning("hologram 跳过：世界未加载"); return; }
        TextDisplay text=(TextDisplay)world.spawnEntity(new Location(world,x,y,z),EntityType.TEXT_DISPLAY);
        text.text(net.kyori.adventure.text.Component.text(String.join("\n",lines)));text.setBillboard(Display.Billboard.CENTER);text.setSeeThrough(false);text.setShadowed(true);text.setPersistent(true);text.setInvulnerable(true);text.addScoreboardTag("island-hub-text");
    }
    private int completedPercent(){if(stage>=4)return 100;int have=0,total=0;for(Stage s:stages)for(int n:s.needs.values())total+=n;for(int i=0;i<stage;i++)for(int n:stages.get(i).needs.values())have+=n;if(stage<4)for(int n:stages.get(stage).delivered.values())have+=n;return (int)Math.round(have*100.0/total);}
    private void buildCurrentSite(){
        if(stage>=4)return;
        int have=0,total=0;for(Material m:stages.get(stage).needs.keySet()){have+=stages.get(stage).delivered.get(m);total+=stages.get(stage).needs.get(m);}
        int level=(int)Math.floor(have*6.0/total);
        if(stage==0){fill(-17,120,-17,-9,120,-9,Material.OAK_PLANKS);for(int y=121;y<=120+level;y++){for(int x=-17;x<=-9;x++){b(x,y,-17,Material.OAK_LOG);b(x,y,-9,Material.OAK_LOG);}for(int z=-17;z<=-9;z++){b(-17,y,z,Material.OAK_LOG);b(-9,y,z,Material.OAK_LOG);}}}
        if(stage==1){for(int x=8;x<=8+level*2;x++)for(int z=-18;z<=-8;z++){if(x==13){b(x,119,z,Material.WATER);b(x,120,z,Material.OAK_TRAPDOOR);}else{b(x,119,z,Material.FARMLAND);b(x,120,z,Material.WHEAT);}}}
        if(stage==2){fill(-3,119,-24-level,3,119,-24,Material.OAK_PLANKS);}
        if(stage==3){for(int y=121;y<=120+level*3;y++)b(0,y,20,Material.STONE_BRICKS);}
    }
    private void restoreHub(World w) {
        Optional<Island> existing = bento.getIslands().getSpawn(w);
        if (!existing.isPresent()) {
            Island created = bento.getIslands().createIsland(new Location(w, 0, 120, 0));
            if (created == null) throw new IllegalStateException("createIsland 返回 null，无法建立独立公共母岛");
            bento.getIslands().setSpawn(created);
            getLogger().info("已自动恢复独立公共母岛，无玩家所有权");
        }
        Island hub = bento.getIslands().getSpawn(w).orElseThrow(() -> new IllegalStateException("setSpawn 后仍取不到母岛"));
        if (hub.getOwner() != null) {
            // 红线：绝不把玩家岛当母岛。宁可报错也不覆盖玩家所有权。
            getLogger().severe("当前 spawn 岛存在属主 " + hub.getOwner() + "，拒绝改写为公共母岛；请人工检查岛屿数据库。");
            return;
        }
        hub.setSpawn(true);
        hub.setReserved(true);
        hub.setPurgeProtected(true);
        hub.setProtectionRange(50);
        Location spawn = new Location(w, HUB_HOME_X, HUB_HOME_Y, HUB_HOME_Z, 0f, 0f);
        bento.getIslands().setHomeLocation(hub, spawn, "");
        // 实测：setSpawnPoint(Environment,Location) 走 Map.compute，在 3.11.1 上
        // 不会改写已有键（同一次 saveObject 里 reserved/homes 都落盘了，唯独它没变）。
        // 因此改用 Map 重载直接整体写入，绕过 compute。
        Map<World.Environment, Location> spawnPoints = new EnumMap<>(World.Environment.class);
        Map<World.Environment, Location> current = hub.getSpawnPoint();
        if (current != null) spawnPoints.putAll(current);
        spawnPoints.put(World.Environment.NORMAL, spawn);
        hub.setSpawnPoint(spawnPoints);
        new Database<>(bento, Island.class).saveObject(hub);
        applyStage();
        // 禁止乐观日志：打印回读值，而不是调用参数。不一致就明确报出来。
        Island readBack = bento.getIslands().getSpawn(w).orElse(null);
        Location actual = readBack == null ? null : readBack.getSpawnPoint(World.Environment.NORMAL);
        String actualDesc = actual == null ? "null"
                : String.format(Locale.ROOT, "(%.1f,%.1f,%.1f)", actual.getX(), actual.getY(), actual.getZ());
        boolean ok = actual != null && Math.abs(actual.getY() - HUB_HOME_Y) < 0.001
                && Math.abs(actual.getZ() - HUB_HOME_Z) < 0.001;
        if (ok) {
            getLogger().info("公共母岛已就绪：spawn/reserved/purgeProtected=true，NORMAL 回家点回读="
                    + actualDesc + "，阶段 " + stage);
        } else {
            getLogger().severe("公共母岛回家点未生效：期望 (" + HUB_HOME_X + "," + HUB_HOME_Y + ","
                    + HUB_HOME_Z + ")，回读=" + actualDesc + "；/is spawn 可能落到旧位置，需人工检查。");
        }
        hubRestoredVerified = ok;
    }
    /** 底层放方块。世界未加载时立即抛错（fail loudly），调用链上游已做守卫。 */
    private Block b(int x,int y,int z,Material m){
        World world = world();
        if (world == null) throw new IllegalStateException("bskyblock_world 未加载，无法放置方块 "+x+","+y+","+z);
        Block b=world.getBlockAt(x,y,z);b.setType(m,false);return b;
    }
    private Block hb(Island island,int x,int y,int z,Material m){return b(island.getX()+x,y,island.getZ()+z,m);}
    private void decorateHome(Island island,Player p){
        if(!decoratedHomes.add(island.getUniqueId()))return;
        int cx=island.getX(),cz=island.getZ();
        for(int x=-14;x<=14;x++)for(int z=-14;z<=14;z++){
            double d=Math.sqrt(x*x+z*z);if(d>14)continue;
            int depth=Math.max(2,9-(int)d/2);
            for(int y=119-depth;y<119;y++)hb(island,x,y,z,y==118?Material.DIRT:(y>115?Material.DIRT:Material.STONE));
            hb(island,x,119,z,Material.GRASS_BLOCK);
        }
        for(int x=-12;x<=12;x++)for(int z=-12;z<=12;z++)if(x*x+z*z>=140&&x*x+z*z<=170&&Math.abs(x)>2&&Math.abs(z)>2)hb(island,x,120,z,Material.OAK_FENCE);
        for(int z=3;z<=11;z++)hb(island,0,119,z,Material.DIRT_PATH);
        for(int x=-7;x<=7;x++)hb(island,x,119,4,Material.DIRT_PATH);
        // 小木屋：有实际可用的床、工作台、箱子和照明。
        for(int x=-10;x<=-4;x++)for(int z=-8;z<=-2;z++)hb(island,x,119,z,Material.OAK_PLANKS);
        for(int y=120;y<=124;y++)for(int x=-10;x<=-4;x++)for(int z=-8;z<=-2;z++){
            boolean wall=x==-10||x==-4||z==-8||z==-2;
            if(wall){Material m=(x==-10||x==-4)&&(z==-8||z==-2)?Material.OAK_LOG:Material.OAK_PLANKS;if(z==-2&&x==-7&&y<122)m=Material.AIR;if(y==122&&((x==-7&&z==-8)||(x==-10&&z==-5)))m=Material.GLASS;hb(island,x,y,z,m);}
            else hb(island,x,y,z,Material.AIR);
        }
        for(int x=-11;x<=-3;x++)for(int z=-9;z<=-1;z++)hb(island,x,125,z,Material.SPRUCE_PLANKS);
        for(int x=-10;x<=-4;x++)for(int z=-8;z<=-2;z++)hb(island,x,126,z,Material.SPRUCE_SLAB);
        hb(island,-9,120,-6,Material.WHITE_BED);hb(island,-5,120,-6,Material.CRAFTING_TABLE);hb(island,-5,120,-4,Material.FURNACE);hb(island,-9,124,-6,Material.LANTERN);
        Block chest=hb(island,-5,120,-7,Material.CHEST);
        if(chest.getState() instanceof org.bukkit.block.Chest){org.bukkit.block.Chest c=(org.bukkit.block.Chest)chest.getState();c.getBlockInventory().addItem(new ItemStack(Material.WATER_BUCKET),new ItemStack(Material.LAVA_BUCKET),new ItemStack(Material.BONE_MEAL,8),new ItemStack(Material.WHEAT_SEEDS,12),new ItemStack(Material.CARROT,4),new ItemStack(Material.POTATO,4),new ItemStack(Material.SUGAR_CANE,4));c.update();}
        // 小型农田与灌溉水源，提供开局可持续食物。
        for(int x=4;x<=9;x++)for(int z=-7;z<=-2;z++){hb(island,x,119,z,Material.FARMLAND);if(x==6){hb(island,x,119,z,Material.WATER);hb(island,x,120,z,Material.OAK_TRAPDOOR);}else hb(island,x,120,z,(z%2==0?Material.WHEAT:Material.CARROTS));}
        // 预留的刷石区：水与岩浆分开放，玩家按引导完成自己的刷石机。
        for(int x=7;x<=11;x++)for(int z=5;z<=8;z++)hb(island,x,119,z,Material.COBBLESTONE);
        hb(island,8,119,6,Material.WATER);hb(island,10,119,6,Material.LAVA);hb(island,9,119,6,Material.AIR);
        // 两棵不同形态的树，岛中央留足扩建空间。
        for(int y=120;y<=125;y++)hb(island,-9,y,8,Material.OAK_LOG);
        for(int x=-12;x<=-6;x++)for(int z=5;z<=11;z++)for(int y=124;y<=127;y++)if(Math.abs(x+9)+Math.abs(z-8)+Math.abs(y-125)<5)hb(island,x,y,z,Material.OAK_LEAVES);
        for(int x=-2;x<=2;x++)for(int z=-11;z<=-8;z++){hb(island,x,119,z,Material.DIRT);hb(island,x,120,z,Material.SUGAR_CANE);}
        hb(island,0,118,-9,Material.WATER);
        hb(island,3,120,1,Material.DANDELION);hb(island,-3,120,1,Material.POPPY);hb(island,4,120,10,Material.CORNFLOWER);hb(island,-4,120,10,Material.OXEYE_DAISY);
        for(int y=120;y<=126;y++)hb(island,0,y,13,Material.AIR);
        World world = world();
        bento.getIslands().setHomeLocation(island,new Location(world,cx+HOME_OFFSET_X,HOME_Y,cz+HOME_OFFSET_Z,0f,0f),"");
        getLogger().info("已生成美化云上家园："+cx+","+cz+"，玩家="+(p==null?"重置建岛":p.getName()));
    }

    private void fill(int x1,int y1,int z1,int x2,int y2,int z2,Material m){for(int x=Math.min(x1,x2);x<=Math.max(x1,x2);x++)for(int y=Math.min(y1,y2);y<=Math.max(y1,y2);y++)for(int z=Math.min(z1,z2);z<=Math.max(z1,z2);z++)b(x,y,z,m);}
    private boolean protectedHub(Player p, Block block) {
        World world = world();
        return world != null && block != null && world.equals(block.getWorld()) && Math.abs(block.getX()) <= 30 && Math.abs(block.getZ()) <= 32 && !p.hasPermission("islandtweaks.admin");
    }
    private boolean publicFarm(Block block) {
        World world = world();
        return stage>=2 && world!=null && world.equals(block.getWorld()) && block.getX()>=8 && block.getX()<=18 && block.getZ()>=-18 && block.getZ()<=-8 && (block.getType()==Material.WHEAT || block.getType()==Material.CARROTS);
    }
    @EventHandler(ignoreCancelled=true) public void onBreak(org.bukkit.event.block.BlockBreakEvent e) {
        if(publicFarm(e.getBlock())) {
            org.bukkit.block.data.Ageable crop=(org.bukkit.block.data.Ageable)e.getBlock().getBlockData();
            if(crop.getAge()!=crop.getMaximumAge()){e.setCancelled(true);send(e.getPlayer(),"作物还没熟，让它再晒会儿太阳。");}
            else Bukkit.getScheduler().runTaskLater(this,()->{if(e.getBlock().getType()==Material.AIR)e.getBlock().setType(crop.getMaterial(),false);},2L);
            return;
        }
        if(protectedHub(e.getPlayer(),e.getBlock())) {e.setCancelled(true);send(e.getPlayer(),"公共母岛由全服共同维护，不能拆这里的方块。");}
    }
    @EventHandler(ignoreCancelled=true) public void onPlace(org.bukkit.event.block.BlockPlaceEvent e) { if(protectedHub(e.getPlayer(),e.getBlock())) {e.setCancelled(true);send(e.getPlayer(),"请在私人岛自由建造；母岛通过 /hub contribute 共同修复。");} }
    @EventHandler(ignoreCancelled=true) public void onInteract(org.bukkit.event.player.PlayerInteractEvent e) {
        World world = world();
        if (world != null && world.equals(e.getPlayer().getWorld()) && e.getAction()==org.bukkit.event.block.Action.RIGHT_CLICK_BLOCK && e.getClickedBlock()!=null) {
            int x=e.getClickedBlock().getX(),z=e.getClickedBlock().getZ();
            if (x==0 && z==-25 && stage>=2) { travel(e.getPlayer(),false); return; }
            if (x==0 && z==23 && stage>=3) { travel(e.getPlayer(),true); return; }
            if (stage<4 && ((x==-13&&z==-7)||(x==13&&z==-7)||(x==0&&z==-6)||(x==0&&z==7))) {
                e.setCancelled(true);
                if((stage==0&&x==-13)||(stage==1&&x==13)||(stage==2&&x==0&&z==-6)||(stage==3&&x==0&&z==7)){contribute(e.getPlayer());return;}
                showProgress(e.getPlayer());return;
            }
        }
        if(protectedHub(e.getPlayer(),e.getClickedBlock()) && (e.getAction()==org.bukkit.event.block.Action.RIGHT_CLICK_BLOCK || e.getAction()==org.bukkit.event.block.Action.PHYSICAL)) {
            e.setCancelled(true); if(e.getAction()==org.bukkit.event.block.Action.RIGHT_CLICK_BLOCK) send(e.getPlayer(),"公共物资请通过 /hub contribute 交付，避免误拿或损坏。");
        }
    }
    private void travel(Player p, boolean end) {
        World world = world();
        if (world == null) { send(p,"主世界尚未加载，请稍后再试。"); return; }
        Island home=bento.getIslands().getIsland(world,p.getUniqueId());
        if(home==null){send(p,"你还没有私人岛，请先输入 /is create。");return;}
        World target=Bukkit.getWorld("bskyblock_world_"+(end?"the_end":"nether"));
        if(target==null){send(p,"目标世界尚未加载，请联系管理员检查。");return;}
        Location destination=new Location(target,home.getX()+0.5,home.getY()+5,home.getZ()+0.5,0,0);
        for(int x=home.getX()-3;x<=home.getX()+3;x++)for(int z=home.getZ()-3;z<=home.getZ()+3;z++){target.getBlockAt(x,home.getY()+2,z).setType(end?Material.END_STONE:Material.NETHERRACK,false);target.getBlockAt(x,home.getY()+3,z).setType(Material.AIR,false);target.getBlockAt(x,home.getY()+4,z).setType(Material.AIR,false);}
        p.teleport(destination);p.setFallDistance(0);send(p,end?"§d引航灯塔已抵达你的末地浮岛。请与队友做好准备，再挑战末影龙。":"§c远航码头已抵达你的下界浮岛。石英、灵魂土与地狱疣在等你，注意脚下。");
    }
    private void buildHub(){
        for(int x=-26;x<=26;x++)for(int z=-26;z<=26;z++){
            int d=(int)Math.sqrt(x*x+z*z);if(d>26)continue;
            b(x,116,z,Material.STONE);if(d<24)b(x,117,z,Material.STONE);if(d<23)b(x,118,z,Material.DIRT);b(x,119,z,Material.GRASS_BLOCK);
            if(d<5 || Math.abs(x)<=1 || Math.abs(z)<=1)b(x,119,z,(x+z)%3==0?Material.STONE_BRICKS:Material.SMOOTH_STONE);
        }
        for(int x=-25;x<=25;x++)for(int z=-25;z<=25;z++){int d=(int)Math.sqrt(x*x+z*z);if(d==25&&Math.abs(x)>2&&Math.abs(z)>2)b(x,120,z,Material.OAK_FENCE);}
        for(int x=-3;x<=3;x++)for(int z=-3;z<=3;z++)if(Math.abs(x)==3||Math.abs(z)==3)b(x,120,z,Material.STONE_BRICK_WALL);
        // 中心装饰柱：先立灯柱，再放信标。
        // 顺序不可颠倒——原代码先放 BEACON/GLASS 再跑灯柱循环，而循环的
        // x,z ∈ {-22,-11,0,11,22}×{-22,0,22} 包含 (0,0)，会把信标覆盖成
        // OAK_LOG、玻璃覆盖成 LANTERN（实测线上 (0,120,0)=oak_log 即此 bug）。
        for(int x=-22;x<=22;x+=11)for(int z=-22;z<=22;z+=22){if(x==0&&z==0)continue;b(x,120,z,Material.OAK_LOG);b(x,121,z,Material.LANTERN);}
        b(0,120,0,Material.BEACON);b(0,121,0,Material.GLASS);b(0,122,0,Material.LANTERN);
        tree(-20,120,5);tree(20,120,5);tree(-6,120,18);
        b(-2,120,5,Material.DANDELION);b(2,120,5,Material.OXEYE_DAISY);b(-4,120,3,Material.POPPY);
        sign(-13,121,-7,"云间仓库工地","点击查看 /hub progress");sign(13,121,-7,"共生农场地基","全服共同修复");sign(0,120,-6,"远航码头工地","修复后开启下界");sign(0,120,7,"引航灯塔地基","点亮后开启末地");
    }
    private void tree(int x,int y,int z){for(int i=0;i<5;i++)b(x,y+i,z,Material.OAK_LOG);for(int dx=-2;dx<=2;dx++)for(int dz=-2;dz<=2;dz++)for(int dy=3;dy<=5;dy++)if(Math.abs(dx)+Math.abs(dz)+dy<8)b(x+dx,y+dy,z+dz,Material.OAK_LEAVES);}

    private void sign(int x,int y,int z,String line1,String line2){
        World world = world();
        b(x,y,z,Material.OAK_SIGN);if(world!=null && world.getBlockAt(x,y,z).getState() instanceof org.bukkit.block.Sign){org.bukkit.block.Sign s=(org.bukkit.block.Sign)world.getBlockAt(x,y,z).getState();s.setLine(0,"§b"+line1);s.setLine(1,line2);s.update();}
    }
    private void completeBuilding(int index){
        if(index==0){
            fill(-18,120,-18,-8,120,-8,Material.OAK_PLANKS);fill(-18,125,-18,-8,125,-8,Material.OAK_PLANKS);
            for(int y=121;y<=124;y++){for(int x=-18;x<=-8;x++){b(x,y,-18,Material.OAK_LOG);b(x,y,-8,Material.OAK_LOG);}for(int z=-18;z<=-8;z++){b(-18,y,z,Material.OAK_LOG);b(-8,y,z,Material.OAK_LOG);}}
            for(int x=-16;x<=-10;x+=2)b(x,120,-15,Material.BARREL);sign(-13,121,-8,"云间仓库","全服共建 · 已修复");
        } else if(index==1){
            for(int x=8;x<=18;x++)for(int z=-18;z<=-8;z++){if(x==13){b(x,119,z,Material.WATER);b(x,120,z,Material.OAK_TRAPDOOR);}else{b(x,119,z,Material.FARMLAND);b(x,120,z,(z%2==0?Material.WHEAT:Material.CARROTS));}}
            for(int z=-18;z<=-8;z++){b(7,120,z,Material.OAK_FENCE);b(19,120,z,Material.OAK_FENCE);}sign(13,121,-8,"共生农场","公共农田 · 已修复");
        } else if(index==2){
            fill(-3,119,-30,3,119,-24,Material.OAK_PLANKS);fill(-3,120,-30,-3,120,-25,Material.OAK_FENCE);fill(3,120,-30,3,120,-25,Material.OAK_FENCE);
            b(-3,121,-29,Material.LANTERN);b(3,121,-29,Material.LANTERN);sign(0,120,-25,"远航码头","下界航线 · 已开放");
        } else if(index==3){
            fill(-2,120,18,2,120,22,Material.STONE_BRICKS);for(int y=121;y<=137;y++)fill(0,y,20,0,y,20,Material.STONE_BRICKS);
            fill(-2,138,18,2,138,22,Material.STONE_BRICKS);b(0,139,20,Material.BEACON);b(0,140,20,Material.SEA_LANTERN);sign(0,120,23,"引航灯塔","末地航线 · 已开放");
        }
    }
}
