// Builds the three dungeon heart meshes and skeletons with the dungeon temple's pedestal.
//
// Input (one folder): DungeonHeartObject{Healthy,Damaged,Critical}.{mesh,skeleton} as exported from
// assets-src/DungeonHeartObject.blend (glTF orientation, Y is up) and DungeonTempleObject.mesh.
// Output (another folder): the same six files, changed like this:
//  - the heart is turned upright for the game (Z is up) and scaled to fit between the temple's claws,
//    its lowest point sits on the pedestal's top step;
//  - the pedestal (steps and claws of the temple's "Stacheln" part, without the old spherical lattice
//    that stood for the heart) is added as a second submesh, bound to the "Root" bone, so that only the
//    heart pulses;
//  - the skeletons' bone positions are moved and scaled the same way as the heart.
//
// Build (Visual Studio developer prompt, Ogre installed in %D%):
//   cl /EHsc /MD /I%D%\include /I%D%\include\OGRE build_heart_on_temple.cpp /link /LIBPATH:%D%\lib OgreMain.lib
// Run: build_heart_on_temple <input folder> <output folder>

#include <Ogre.h>
#include <OgreMeshSerializer.h>
#include <OgreSkeletonSerializer.h>
#include <OgreDataStream.h>
#include <OgreDefaultHardwareBufferManager.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace
{
const float HEART_SCALE = 0.45f;
// The pedestal's top step is at 0.418; the heart sinks 0.02 into it
const float HEART_BOTTOM = 0.40f;
// Triangles that lie completely within this distance of the old lattice centre are the old heart
const float LATTICE_RADIUS = 0.68f;
const Ogre::Vector3 LATTICE_CENTRE(0.0f, 0.0f, 1.2f);

// (x, y, z) in glTF orientation to the game's: Y up becomes Z up
Ogre::Vector3 toGame(const Ogre::Vector3& v, float lift)
{
    return Ogre::Vector3(v.x * HEART_SCALE, -v.z * HEART_SCALE, v.y * HEART_SCALE + lift);
}

Ogre::Vector3 normalToGame(const Ogre::Vector3& v)
{
    return Ogre::Vector3(v.x, -v.z, v.y);
}

struct Vertex
{
    Ogre::Vector3 position;
    Ogre::Vector3 normal;
    Ogre::Vector2 uv;
};

Ogre::MeshPtr loadMesh(const std::string& path, const std::string& name)
{
    Ogre::MeshPtr mesh = Ogre::MeshManager::getSingleton().create(name, Ogre::RGN_DEFAULT, true);
    Ogre::MeshSerializer serializer;
    Ogre::DataStreamPtr stream(new Ogre::FileStreamDataStream(new std::ifstream(path.c_str(), std::ios::binary), true));
    serializer.importMesh(stream, mesh.get());
    return mesh;
}

void includePoint(Ogre::AxisAlignedBox& box, Ogre::Real& radius, const Ogre::Vector3& point)
{
    box.merge(point);
    radius = std::max(radius, point.length());
}

// Moves the heart's shared vertex data to the game's orientation, grows the bounds and returns the lift that
// puts the heart's lowest point on the pedestal (every tier has its own lowest point)
float transformHeart(Ogre::Mesh* mesh, Ogre::AxisAlignedBox& box, Ogre::Real& radius)
{
    Ogre::VertexData* data = mesh->sharedVertexData;
    const Ogre::VertexElement* position = data->vertexDeclaration->findElementBySemantic(Ogre::VES_POSITION);
    const Ogre::VertexElement* normal = data->vertexDeclaration->findElementBySemantic(Ogre::VES_NORMAL);
    if(position == nullptr || normal == nullptr || position->getSource() != normal->getSource())
        OGRE_EXCEPT(Ogre::Exception::ERR_INVALIDPARAMS, "Unexpected heart vertex layout", "transformHeart");
    Ogre::HardwareVertexBufferSharedPtr buffer = data->vertexBufferBinding->getBuffer(position->getSource());
    unsigned char* base = static_cast<unsigned char*>(buffer->lock(Ogre::HardwareBuffer::HBL_NORMAL));
    float minY = 1.0e10f;
    for(size_t i = 0; i < data->vertexCount; ++i)
    {
        float* p;
        position->baseVertexPointerToElement(base + i * buffer->getVertexSize(), &p);
        minY = std::min(minY, p[1]);
    }
    const float lift = HEART_BOTTOM - minY * HEART_SCALE;
    for(size_t i = 0; i < data->vertexCount; ++i)
    {
        unsigned char* vertex = base + i * buffer->getVertexSize();
        float* p;
        float* n;
        position->baseVertexPointerToElement(vertex, &p);
        normal->baseVertexPointerToElement(vertex, &n);
        const Ogre::Vector3 newPosition = toGame(Ogre::Vector3(p[0], p[1], p[2]), lift);
        const Ogre::Vector3 newNormal = normalToGame(Ogre::Vector3(n[0], n[1], n[2]));
        p[0] = newPosition.x;
        p[1] = newPosition.y;
        p[2] = newPosition.z;
        n[0] = newNormal.x;
        n[1] = newNormal.y;
        n[2] = newNormal.z;
        includePoint(box, radius, newPosition);
    }
    buffer->unlock();
    return lift;
}

// Reads the temple's first submesh ("Stacheln", the metal part) and returns its vertices and the triangles that are not the lattice
void readPedestal(Ogre::Mesh* temple, std::vector<Vertex>& vertices, std::vector<unsigned short>& indices)
{
    Ogre::SubMesh* sub = temple->getSubMesh(0);
    Ogre::VertexData* data = sub->vertexData;
    const Ogre::VertexElement* position = data->vertexDeclaration->findElementBySemantic(Ogre::VES_POSITION);
    const Ogre::VertexElement* normal = data->vertexDeclaration->findElementBySemantic(Ogre::VES_NORMAL);
    const Ogre::VertexElement* uv = data->vertexDeclaration->findElementBySemantic(Ogre::VES_TEXTURE_COORDINATES);
    Ogre::HardwareVertexBufferSharedPtr buffer = data->vertexBufferBinding->getBuffer(position->getSource());
    unsigned char* base = static_cast<unsigned char*>(buffer->lock(Ogre::HardwareBuffer::HBL_READ_ONLY));
    std::vector<Vertex> all(data->vertexCount);
    for(size_t i = 0; i < data->vertexCount; ++i)
    {
        unsigned char* vertex = base + i * buffer->getVertexSize();
        float* p;
        float* n;
        float* t;
        position->baseVertexPointerToElement(vertex, &p);
        normal->baseVertexPointerToElement(vertex, &n);
        uv->baseVertexPointerToElement(vertex, &t);
        all[i].position = Ogre::Vector3(p[0], p[1], p[2]);
        all[i].normal = Ogre::Vector3(n[0], n[1], n[2]);
        all[i].uv = Ogre::Vector2(t[0], t[1]);
    }
    buffer->unlock();

    Ogre::HardwareIndexBufferSharedPtr index = sub->indexData->indexBuffer;
    std::vector<unsigned int> triangles(sub->indexData->indexCount);
    const bool wide = index->getType() == Ogre::HardwareIndexBuffer::IT_32BIT;
    void* raw = index->lock(Ogre::HardwareBuffer::HBL_READ_ONLY);
    for(size_t i = 0; i < triangles.size(); ++i)
        triangles[i] = wide ? static_cast<unsigned int*>(raw)[i] : static_cast<unsigned short*>(raw)[i];
    index->unlock();

    std::map<unsigned int, unsigned short> remap;
    for(size_t i = 0; i + 2 < triangles.size(); i += 3)
    {
        bool lattice = true;
        for(size_t k = 0; k < 3; ++k)
            if((all[triangles[i + k]].position - LATTICE_CENTRE).length() >= LATTICE_RADIUS)
                lattice = false;
        if(lattice)
            continue;
        for(size_t k = 0; k < 3; ++k)
        {
            std::map<unsigned int, unsigned short>::iterator it = remap.find(triangles[i + k]);
            if(it == remap.end())
            {
                it = remap.insert(std::make_pair(triangles[i + k], static_cast<unsigned short>(vertices.size()))).first;
                vertices.push_back(all[triangles[i + k]]);
            }
            indices.push_back(it->second);
        }
    }
}

void addPedestal(Ogre::Mesh* heart, const std::vector<Vertex>& vertices, const std::vector<unsigned short>& indices,
    Ogre::AxisAlignedBox& box, Ogre::Real& radius)
{
    Ogre::SubMesh* sub = heart->createSubMesh("Pedestal");
    sub->setMaterialName("Stacheln");
    sub->useSharedVertices = false;
    sub->vertexData = new Ogre::VertexData();
    sub->vertexData->vertexCount = vertices.size();
    Ogre::VertexDeclaration* decl = sub->vertexData->vertexDeclaration;
    size_t offset = 0;
    offset += decl->addElement(0, offset, Ogre::VET_FLOAT3, Ogre::VES_POSITION).getSize();
    offset += decl->addElement(0, offset, Ogre::VET_FLOAT3, Ogre::VES_NORMAL).getSize();
    offset += decl->addElement(0, offset, Ogre::VET_FLOAT2, Ogre::VES_TEXTURE_COORDINATES, 0).getSize();
    Ogre::HardwareVertexBufferSharedPtr buffer = Ogre::HardwareBufferManager::getSingleton().createVertexBuffer(
        offset, vertices.size(), Ogre::HBU_CPU_ONLY);
    float* out = static_cast<float*>(buffer->lock(Ogre::HardwareBuffer::HBL_DISCARD));
    for(size_t i = 0; i < vertices.size(); ++i)
    {
        *out++ = vertices[i].position.x;
        *out++ = vertices[i].position.y;
        *out++ = vertices[i].position.z;
        *out++ = vertices[i].normal.x;
        *out++ = vertices[i].normal.y;
        *out++ = vertices[i].normal.z;
        *out++ = vertices[i].uv.x;
        *out++ = vertices[i].uv.y;
        includePoint(box, radius, vertices[i].position);
    }
    buffer->unlock();
    sub->vertexData->vertexBufferBinding->setBinding(0, buffer);

    sub->indexData->indexCount = indices.size();
    sub->indexData->indexStart = 0;
    sub->indexData->indexBuffer = Ogre::HardwareBufferManager::getSingleton().createIndexBuffer(
        Ogre::HardwareIndexBuffer::IT_16BIT, indices.size(), Ogre::HBU_CPU_ONLY);
    sub->indexData->indexBuffer->writeData(0, indices.size() * sizeof(unsigned short), &indices[0], true);

    // The pedestal does not move: every vertex belongs completely to the "Root" bone (handle 0)
    for(size_t i = 0; i < vertices.size(); ++i)
    {
        Ogre::VertexBoneAssignment assignment;
        assignment.vertexIndex = static_cast<unsigned int>(i);
        assignment.boneIndex = 0;
        assignment.weight = 1.0f;
        sub->addBoneAssignment(assignment);
    }
}

void convertSkeleton(const std::string& inPath, const std::string& outPath, const std::string& name, float lift)
{
    Ogre::SkeletonPtr skeleton = Ogre::SkeletonManager::getSingleton().create(name, Ogre::RGN_DEFAULT, true);
    Ogre::SkeletonSerializer serializer;
    Ogre::DataStreamPtr stream(new Ogre::FileStreamDataStream(new std::ifstream(inPath.c_str(), std::ios::binary), true));
    serializer.importSkeleton(stream, skeleton.get());
    // The bones' positions are relative to their parents, which only turn/scale uniformly with the heart.
    // The root has the lift, its child only the scaled offset.
    for(unsigned short i = 0; i < skeleton->getNumBones(); ++i)
    {
        Ogre::Bone* bone = skeleton->getBone(i);
        const Ogre::Vector3 position = bone->getPosition();
        Ogre::Vector3 moved(position.x * HEART_SCALE, -position.z * HEART_SCALE, position.y * HEART_SCALE);
        if(bone->getParent() == nullptr)
            moved.z += lift;
        bone->setPosition(moved);
    }
    skeleton->setBindingPose();
    serializer.exportSkeleton(skeleton.get(), outPath, Ogre::SKELETON_VERSION_1_8);
}
}

int run(int argc, char** argv)
{
    if(argc != 3)
    {
        std::cerr << "usage: build_heart_on_temple <input folder> <output folder>\n";
        return 2;
    }
    const std::string in = std::string(argv[1]) + "/";
    const std::string out = std::string(argv[2]) + "/";
    Ogre::LogManager* logManager = new Ogre::LogManager();
    logManager->createLog("build_heart_on_temple.log", true, false, false);
    Ogre::Root* root = new Ogre::Root("", "", "");
    Ogre::DefaultHardwareBufferManager* bufferManager = new Ogre::DefaultHardwareBufferManager();
    Ogre::ResourceGroupManager::getSingleton().addResourceLocation(in, "FileSystem");
    // Ogre keeps a material name in a mesh only while a material of that name exists; empty ones are enough here
    const char* materials[6] = {"Stacheln", "Sphere", "Sphere2", "DungeonHeartHealthy", "DungeonHeartDamaged",
        "DungeonHeartCritical"};
    for(int i = 0; i < 6; ++i)
        Ogre::MaterialManager::getSingleton().create(materials[i], Ogre::RGN_DEFAULT);

    Ogre::MeshPtr temple = loadMesh(in + "DungeonTempleObject.mesh", "temple");
    std::vector<Vertex> vertices;
    std::vector<unsigned short> indices;
    readPedestal(temple.get(), vertices, indices);
    std::cout << "pedestal: " << vertices.size() << " vertices, " << indices.size() / 3 << " triangles\n";

    const char* tiers[3] = {"Healthy", "Damaged", "Critical"};
    for(int t = 0; t < 3; ++t)
    {
        const std::string base = std::string("DungeonHeartObject") + tiers[t];
        Ogre::MeshPtr heart = loadMesh(in + base + ".mesh", base);
        Ogre::AxisAlignedBox box;
        Ogre::Real radius = 0.0f;
        const float lift = transformHeart(heart.get(), box, radius);
        addPedestal(heart.get(), vertices, indices, box, radius);
        heart->_setBounds(box, false);
        heart->_setBoundingSphereRadius(radius);
        Ogre::MeshSerializer serializer;
        serializer.exportMesh(heart.get(), out + base + ".mesh");
        convertSkeleton(in + base + ".skeleton", out + base + ".skeleton", base + "_converted.skeleton", lift);
        std::cout << base << ": bounds " << box.getMinimum() << " .. " << box.getMaximum() << "\n";
    }
    temple.reset();
    delete root;
    delete bufferManager;
    delete logManager;
    return 0;
}

int main(int argc, char** argv)
{
    try
    {
        return run(argc, argv);
    }
    catch(const Ogre::Exception& exception)
    {
        std::cerr << exception.getFullDescription() << "\n";
        return 1;
    }
}
